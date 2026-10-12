"""Bot UI regressions with real PTB routing and mocked I/O.

Only definitions and explicitly listed constants are compiled from the bot.
Its dotenv/token bootstrap and the real utils module are never executed.
"""
import ast
import datetime
import logging
from pathlib import Path
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch
from requests import RequestException

import pandas as pd
from telegram import Update, User
from telegram.ext import CommandHandler, ExtBot

ROOT = Path(__file__).resolve().parents[1]


def load_bot():
    source = ROOT.joinpath("telegram_bot.py").read_text(encoding="utf-8")
    parsed = ast.parse(source)
    constants = {
        "ADMIN_USERNAME", "ADMIN_IDS", "SIMPLIFIED_PUBLIC_COMMANDS", "SENSOR_ID",
        "REG_PHONE", "REG_FIRSTNAME", "REG_LASTNAME", "REG_DISTRICT", "REG_LOCATION",
        "TKT_LOCATION", "TKT_SENSOR", "TKT_PRIORITY", "TKT_DESCRIBE", "TKT_PHOTO", "TKT_CONFIRM",
        "PHOTO_TKT_SENSOR", "PHOTO_TKT_DESCRIBE", "PHOTO_TKT_CONFIRM",
        "df", "hybrid_model", "subscribers", "_last_err",
        "_MAIN_KEYBOARD", "_MAIN_TEXT", "_BACK", "PRIORITY_EMOJI", "PRIORITY_LABEL",
    }
    selected = []
    utility_names = []
    for node in parsed.body:
        if isinstance(node, ast.ImportFrom) and node.module == "utils":
            utility_names.extend(alias.name for alias in node.names)
        elif isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            selected.append(node)
        elif isinstance(node, ast.Assign):
            assigned = {n.id for target in node.targets for n in ast.walk(target) if isinstance(n, ast.Name)}
            if assigned and assigned <= constants:
                selected.append(node)
    module = types.ModuleType("bot_menu_test_module")
    module.logger = logging.getLogger("bot-menu-tests")
    module.BOT_TOKEN = "123456:TEST_TOKEN"
    module.SITE_BASE = "http://example.invalid"
    for name in utility_names:
        setattr(module, name, Mock(name=name))
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(ROOT / "telegram_bot.py"), "exec"),
         module.__dict__)
    module.ADMIN_IDS = frozenset()
    module.DISTRICTS = ["Chilonzor"]
    module.DISTRICT_COORDS = {"Chilonzor": (41.3, 69.2)}
    return module


def buttons(markup):
    return [button for row in markup.inline_keyboard for button in row]


def callback_names(markup):
    return {button.callback_data for button in buttons(markup) if button.callback_data}


class BotMenuTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = load_bot()
        self.user_record = {
            "id": 42, "first_name": "Test", "last_name": "User", "phone": "+998000000000",
            "district": "Chilonzor", "latitude": 41.3, "longitude": 69.2,
            "silent_mode": False, "role": "user",
        }
        self.bot.get_user_by_id.side_effect = lambda uid: self.user_record if uid == 42 else None
        self.bot.load_users.return_value = [self.user_record]
        self.bot.df = pd.DataFrame([
            {"SensorID": "S0001", "Timestamp": datetime.datetime(2026, 10, 1, hour),
             "District": "Chilonzor", "Fault": fault,
             "Kuchlanish (V)": 220.0, "Chastota (Hz)": 50.0,
             "Muhit_harorat (C)": 25.0, "Vibratsiya": .2,
             "Latitude": 0., "Longitude": 0.}
            for hour, fault in [(1, 0), (2, 2)]
        ])
        self.errors = []

        async def record_error(update, context):
            self.errors.append(context.error)

        self.bot.error_handler = record_error
        self.app = self.bot.build_application(self.bot.BOT_TOKEN)
        # No initialize/get_me, polling, dotenv or real token reads.
        self.app._initialized = True
        self.app.bot._initialized = True
        self.app.bot._bot_user = User(999, "Test Bot", True, username="test_bot")
        self.io = {}
        for method in (
            "send_message", "send_photo", "send_location", "edit_message_text",
            "edit_message_caption", "edit_message_reply_markup", "answer_callback_query",
            "set_my_commands",
        ):
            mock = AsyncMock()
            self.io[method] = mock
            patcher = patch.object(ExtBot, method, mock)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.utils = types.ModuleType("utils")
        self.utils.load_tickets = Mock(return_value=[])
        self.utils.save_tickets = Mock()
        self.utils.close_ticket = Mock()
        self.utils.create_ticket = Mock(return_value={"id": "T-test"})
        patcher = patch.dict("sys.modules", {"utils": self.utils})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.update_id = 0

    def update(self, text=None, callback=None, location=None, photo=False, username="ordinary"):
        self.update_id += 1
        user = {"id": 42, "is_bot": False, "first_name": "Test", "username": username}
        message = {
            "message_id": self.update_id, "date": 1,
            "chat": {"id": 42, "type": "private"}, "from": user,
        }
        if text is not None:
            message["text"] = text
            if text.startswith("/"):
                message["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
        if location:
            message["location"] = {"latitude": location[0], "longitude": location[1]}
        if photo:
            message["photo"] = [{"file_id": "test-photo", "file_unique_id": "unique", "width": 1, "height": 1}]
        payload = {"update_id": self.update_id}
        if callback is not None:
            message["text"] = "Menyu"
            payload["callback_query"] = {
                "id": str(self.update_id), "from": user, "chat_instance": "test",
                "data": callback, "message": message,
            }
        else:
            payload["message"] = message
        return Update.de_json(payload, self.app.bot)

    async def dispatch(self, **kwargs):
        update = self.update(**kwargs)
        await self.app.process_update(update)
        self.assertEqual(self.errors, [])
        return update

    def state(self):
        dialog = self.app.handlers[0][0]
        return dialog._conversations.get((42, 42))

    def sent_text(self):
        return "\n".join(
            str(call.kwargs.get("text", ""))
            for method in ("send_message", "edit_message_text")
            for call in self.io[method].await_args_list
        )

    def last_markup(self, method="send_message"):
        return self.io[method].await_args.kwargs["reply_markup"]

    async def test_main_menu_has_five_choices_and_one_shared_source(self):
        expected = {"monitoring", "sensor_check", "forecast", "new_ticket", "settings"}
        self.assertEqual(callback_names(self.bot.main_menu_markup()), expected)
        self.assertEqual(len(buttons(self.bot.main_menu_markup())), 5)
        self.assertIn("Nosozlik bildirish", str(self.bot.main_menu_markup()))
        self.assertNotIn("Hisobot", str(self.bot.main_menu_markup()))
        await self.dispatch(text="/menu")
        self.assertEqual(callback_names(self.last_markup()), expected)
        await self.dispatch(callback="menu")
        self.assertEqual(callback_names(self.last_markup("edit_message_text")), expected)

    async def test_monitoring_callbacks_and_missing_data_have_navigation(self):
        await self.dispatch(callback="monitoring")
        self.assertEqual(callback_names(self.last_markup("edit_message_text")),
                         {"dashboard", "stats", "danger_sensors", "menu"})
        for callback in ("stats", "danger_sensors", "dashboard"):
            self.bot.df = None
            await self.dispatch(callback=callback)
            self.assertIn("menu", callback_names(self.last_markup("edit_message_text")))
        self.assertEqual(self.io["answer_callback_query"].await_count, 4)

    async def test_monitoring_actions_reuse_existing_functions(self):
        await self.dispatch(callback="stats")
        self.assertIn("Umumiy Statistika", self.sent_text())
        await self.dispatch(callback="danger_sensors")
        self.assertIn("S0001", self.sent_text())
        await self.dispatch(callback="dashboard")
        self.io["send_photo"].assert_awaited_once()
        self.assertIn("menu", callback_names(self.last_markup("send_photo")))

    async def test_public_command_scopes_and_admin_separation(self):
        self.assertEqual(self.bot.SIMPLIFIED_PUBLIC_COMMANDS, ["start", "menu", "help", "cancel"])
        await self.bot.setup_bot_commands(self.app)
        for call in self.io["set_my_commands"].await_args_list:
            self.assertEqual([c.command for c in call.args[0]], ["start", "menu", "help", "cancel"])
        self.io["set_my_commands"].reset_mock()
        self.user_record["role"] = "admin"
        await self.bot.setup_bot_commands(self.app)
        calls = self.io["set_my_commands"].await_args_list
        for call in calls[:2]:
            self.assertEqual([c.command for c in call.args[0]], ["start", "menu", "help", "cancel"])
        self.assertIn("admin", [c.command for c in calls[-1].args[0]])
        self.assertEqual(calls[-1].kwargs["scope"].chat_id, 42)
        self.assertIs(self.app.post_init, self.bot.setup_bot_commands)

    async def test_sensor_dialog_normalization_errors_and_result_buttons(self):
        await self.dispatch(callback="sensor_check")
        self.assertEqual(self.state(), self.bot.SENSOR_ID)
        for invalid in ("bad_*", "S9999"):
            await self.dispatch(text=invalid)
            self.assertEqual(self.state(), self.bot.SENSOR_ID)
            self.assertIn("menu", callback_names(self.last_markup()))
        await self.dispatch(text="s1")
        self.assertIsNone(self.state())
        self.assertIn("Sensor: S0001", self.sent_text())
        self.assertEqual(callback_names(self.last_markup()),
                         {"sensor_chart:S0001", "sensor_history:S0001", "sensor_check", "menu"})
        self.assertNotIn("/sensor", self.sent_text())

    async def test_sensor_data_unavailable_and_disappearing_during_dialog(self):
        self.bot.df = None
        await self.dispatch(callback="sensor_check")
        self.assertIsNone(self.state())
        self.assertIn("menu", callback_names(self.last_markup("edit_message_text")))
        self.bot.df = pd.DataFrame({"SensorID": ["S0001"]})
        await self.dispatch(callback="sensor_check")
        self.bot.df = None
        await self.dispatch(text="1")
        self.assertIsNone(self.state())
        self.assertIn("yuklanmagan", self.sent_text())

    async def test_sensor_chart_history_and_old_card_callbacks(self):
        await self.dispatch(callback="sensor_chart:S0001")
        self.io["send_photo"].assert_awaited_once()
        self.assertIn("menu", callback_names(self.last_markup("send_photo")))
        await self.dispatch(callback="sensor_history:S0001")
        self.assertIn("S0001 tarixi", self.sent_text())
        await self.dispatch(callback="sensor_S0001")
        self.assertIn("Sensor: S0001", self.sent_text())
        await self.dispatch(callback="chart_check")
        self.assertEqual(self.state(), self.bot.SENSOR_ID)
        await self.dispatch(text="1")
        self.assertIsNone(self.state())
        self.assertEqual(self.io["send_photo"].await_count, 2)

    async def test_legacy_commands_remain_functional_and_hidden_from_help(self):
        await self.dispatch(text="/sensor S0001")
        self.assertIn("Sensor: S0001", self.sent_text())
        await self.dispatch(text="/chart S0001")
        self.io["send_photo"].assert_awaited_once()
        await self.dispatch(text="/history S0001 7")
        self.assertIn("S0001 tarixi", self.sent_text())
        await self.dispatch(text="/help")
        help_text = self.io["send_message"].await_args.kwargs["text"]
        for command in ("/sensor", "/ticket", "/forecast", "/stats", "/subscribe"):
            self.assertNotIn(command, help_text)
        self.assertIn("menu", callback_names(self.last_markup()))
        commands = set()
        for handler in self.app.handlers[0]:
            if isinstance(handler, CommandHandler):
                commands.update(handler.commands)
        self.assertTrue({"admin", "broadcast", "alert_test", "send_user", "report", "ask"} <= commands)

    async def test_settings_subscribe_unsubscribe_and_silent_buttons(self):
        await self.dispatch(callback="settings")
        self.assertEqual(callback_names(self.last_markup("edit_message_text")),
                         {"subscribe", "silent_toggle", "help", "menu"})
        await self.dispatch(callback="subscribe")
        self.assertIn(42, self.bot.subscribers)
        self.bot.save_subscribers.assert_called_once()
        self.assertIn("unsubscribe", callback_names(self.last_markup("edit_message_text")))
        await self.dispatch(callback="unsubscribe")
        self.assertNotIn(42, self.bot.subscribers)
        await self.dispatch(callback="silent_toggle")
        self.bot.update_user.assert_called_once_with(42, silent_mode=True)
        self.assertIn("menu", callback_names(self.last_markup("edit_message_text")))
        self.assertNotIn("/subscribe", self.sent_text())

    async def test_forecast_reuses_seven_day_weather_and_returns_to_menu(self):
        self.bot.requests = Mock()
        self.bot.requests.get.return_value.json.return_value = {"daily": {
            "time": ["2026-10-12"], "precipitation_sum": [0],
            "temperature_2m_min": [10], "temperature_2m_max": [20], "wind_speed_10m_max": [5],
        }}
        await self.dispatch(callback="forecast")
        self.assertEqual(self.bot.requests.get.call_args.kwargs["params"]["forecast_days"], 7)
        self.assertIn("menu", callback_names(self.last_markup("edit_message_text")))
        self.bot.requests.get.side_effect = RequestException("offline")
        await self.dispatch(callback="forecast")
        self.assertIn("menu", callback_names(self.last_markup("edit_message_text")))

    async def test_unknown_input_is_short_and_has_menu_and_help(self):
        for text in ("hello", "/missing", "/untrusted_*"):
            await self.dispatch(text=text)
            self.assertEqual(callback_names(self.last_markup()), {"menu", "help"})
            self.assertLess(len(self.io["send_message"].await_args.kwargs["text"]), 100)
        self.assertNotIn("/sensor", self.sent_text())

    async def test_ticket_flow_from_menu_through_confirmation_and_send(self):
        self.bot.requests = Mock()
        self.bot.requests.post.return_value.status_code = 200
        self.bot.requests.post.return_value.json.return_value = {"ok": True, "ticket": {"id": "T-test"}}
        self.bot._notify_admin_new_ticket = AsyncMock()
        await self.dispatch(callback="new_ticket")
        self.assertEqual(self.state(), self.bot.TKT_LOCATION)
        await self.dispatch(text="⏭️ GPS siz davom etish")
        self.assertEqual(self.state(), self.bot.TKT_SENSOR)
        await self.dispatch(callback="tkt_sensor_manual")
        self.assertEqual(self.state(), self.bot.TKT_SENSOR)
        await self.dispatch(text="s1")
        self.assertEqual(self.state(), self.bot.TKT_PRIORITY)
        await self.dispatch(callback="tkt_pri_past")
        self.assertEqual(self.state(), self.bot.TKT_DESCRIBE)
        await self.dispatch(text="Kuchlanish keskin tushib ketdi")
        self.assertEqual(self.state(), self.bot.TKT_PHOTO)
        await self.dispatch(callback="tkt_photo_wait")
        self.assertIn("tkt_photo_skip", callback_names(self.last_markup("edit_message_text")))
        await self.dispatch(callback="tkt_photo_skip")
        self.assertEqual(self.state(), self.bot.TKT_CONFIRM)
        await self.dispatch(callback="tkt_send")
        self.assertIsNone(self.state())
        self.assertNotIn("tkt", self.app.user_data[42])
        self.assertEqual(self.bot.requests.post.call_args.kwargs["json"]["sensor_id"], "S0001")
        self.bot._notify_admin_new_ticket.assert_awaited_once()
        self.assertIn("menu", callback_names(self.last_markup("edit_message_text")))

    async def test_unknown_sensor_ticket_callback_uses_location_flow(self):
        await self.dispatch(text="/ticket")
        await self.dispatch(text="⏭️ GPS siz davom etish")
        await self.dispatch(callback="tkt_sensor_unknown")
        self.assertEqual(self.state(), self.bot.TKT_SENSOR)
        self.assertEqual(self.app.user_data[42]["tkt"]["sensor_id"], "UNKNOWN")
        self.assertTrue(self.app.user_data[42]["tkt"]["waiting_location"])

    async def test_ticket_location_does_not_also_call_general_location_handler(self):
        self.bot.location_handler = AsyncMock()
        # Rebuild after replacing the callback used during handler registration.
        self.app = self.bot.build_application(self.bot.BOT_TOKEN)
        self.app._initialized = True
        self.app.bot._initialized = True
        self.app.bot._bot_user = User(999, "Test Bot", True, username="test_bot")
        await self.dispatch(callback="new_ticket")
        await self.dispatch(location=(41.3, 69.2))
        self.assertEqual(self.state(), self.bot.TKT_SENSOR)
        self.bot.location_handler.assert_not_awaited()

    async def test_unexpected_text_callbacks_and_commands_preserve_ticket_step(self):
        await self.dispatch(callback="new_ticket")
        await self.dispatch(text="⏭️ GPS siz davom etish")
        await self.dispatch(callback="tkt_sensor_S0001")
        self.assertEqual(self.state(), self.bot.TKT_PRIORITY)
        for kwargs in ({"text": "hello"}, {"text": "/missing"}, {"callback": "sensor_check"},
                       {"callback": "forecast"}, {"photo": True}):
            await self.dispatch(**kwargs)
            self.assertEqual(self.state(), self.bot.TKT_PRIORITY)
        self.assertEqual(self.app.user_data[42]["tkt"]["sensor_id"], "S0001")

    async def test_menu_and_cancel_end_every_dialog_state(self):
        dialog = self.app.handlers[0][0]
        for state in dialog.states:
            for kwargs in ({"text": "/menu"}, {"text": "/cancel"}, {"callback": "menu"},
                           {"text": "🏠 Bosh menyu"}):
                dialog._conversations[(42, 42)] = state
                self.app.user_data[42].update({"tkt": {}, "ptkt": {}, "sensor_action": "sensor"})
                await self.dispatch(**kwargs)
                self.assertIsNone(self.state(), (state, kwargs))
                self.assertFalse({"tkt", "ptkt", "sensor_action"} & self.app.user_data[42].keys())

    async def test_registration_still_consumes_names_without_unknown_text(self):
        self.bot.get_user_by_id.return_value = None
        self.bot.get_user_by_id.side_effect = None
        await self.dispatch(text="/start")
        self.assertEqual(self.state(), self.bot.REG_PHONE)
        await self.dispatch(text="+998901234567")
        self.assertEqual(self.state(), self.bot.REG_FIRSTNAME)
        await self.dispatch(text="Test")
        self.assertEqual(self.state(), self.bot.REG_LASTNAME)
        await self.dispatch(text="User")
        self.assertEqual(self.state(), self.bot.REG_DISTRICT)
        await self.dispatch(text="Chilonzor")
        self.assertEqual(self.state(), self.bot.REG_LOCATION)
        self.assertNotIn("Kerakli bo'limni tugma", self.sent_text())

    async def test_non_admin_cannot_use_admin_commands_or_forged_ticket_callbacks(self):
        # Even the formerly trusted username does not grant authorization.
        for cmd in ("/admin", "/broadcast test", "/send_user 1 test", "/alert_test", "/tickets"):
            await self.dispatch(text=cmd, username=self.bot.ADMIN_USERNAME)
        for callback in ("adm_close_T-test", "adm_inprog_T-test", "resolve:test",
                         "close_ticket_T-test", "inprog_ticket_T-test", "tickets_list",
                         "admin_broadcast_hint", "contact_msg:1"):
            await self.dispatch(callback=callback, username=self.bot.ADMIN_USERNAME)
        self.utils.load_tickets.assert_not_called()
        self.utils.save_tickets.assert_not_called()
        self.utils.close_ticket.assert_not_called()
        for call in self.io["answer_callback_query"].await_args_list:
            self.assertTrue(call.kwargs.get("show_alert"))

    async def test_admin_identity_uses_stored_role_or_numeric_allowlist(self):
        update = self.update(text="/admin", username=self.bot.ADMIN_USERNAME)
        self.assertFalse(self.bot.is_admin(update))
        self.user_record["role"] = "admin"
        self.assertTrue(self.bot.is_admin(update))
        self.user_record["role"] = "user"
        self.bot.ADMIN_IDS = frozenset({42})
        self.assertTrue(self.bot.is_admin(update))
        self.assertFalse(self.bot.is_admin_id(43))

    async def test_admin_ticket_controls_remain_available(self):
        self.user_record["role"] = "admin"
        self.utils.load_tickets.return_value = [{
            "id": "T-test", "status": "open", "sensor_id": "S0001",
            "priority": "past", "issue": "test",
        }]
        await self.dispatch(text="/tickets")
        self.assertIn("close_ticket_T-test", callback_names(self.last_markup()))
        await self.dispatch(callback="inprog_ticket_T-test")
        self.utils.save_tickets.assert_called_once()
        self.utils.close_ticket.return_value = self.utils.load_tickets.return_value[0]
        await self.dispatch(callback="close_ticket_T-test")
        self.utils.close_ticket.assert_called_once_with("T-test")

    async def test_photo_ticket_manual_and_cancel_keep_menu_navigation(self):
        self.user_record["latitude"] = None
        await self.dispatch(photo=True)
        self.assertEqual(self.state(), self.bot.PHOTO_TKT_SENSOR)
        self.assertIn("menu", callback_names(self.last_markup()))
        await self.dispatch(callback="ptkt_manual")
        self.assertIn("menu", callback_names(self.last_markup("edit_message_text")))
        await self.dispatch(text="1")
        self.assertEqual(self.state(), self.bot.PHOTO_TKT_DESCRIBE)
        self.assertIn("menu", callback_names(self.last_markup()))
        await self.dispatch(callback="ptkt_cancel")
        self.assertIsNone(self.state())
        self.assertNotIn("ptkt", self.app.user_data[42])

    async def test_media_main_menu_falls_back_to_caption(self):
        self.io["edit_message_text"].side_effect = RuntimeError("media message")
        await self.dispatch(callback="menu")
        self.io["edit_message_caption"].assert_awaited_once()
        self.assertEqual(callback_names(self.last_markup("edit_message_caption")),
                         {"monitoring", "sensor_check", "forecast", "new_ticket", "settings"})

    async def test_ticket_skip_command_remains_backward_compatible(self):
        await self.dispatch(text="/ticket")
        await self.dispatch(text="⏭️ GPS siz davom etish")
        await self.dispatch(callback="tkt_sensor_S0001")
        await self.dispatch(callback="tkt_pri_past")
        await self.dispatch(text="Kuchlanish keskin tushib ketdi")
        await self.dispatch(text="/skip")
        self.assertEqual(self.state(), self.bot.TKT_CONFIRM)
        self.assertIn("tkt_send", callback_names(self.last_markup()))

    async def test_sensor_callback_handles_deleted_sensor_and_invalid_id(self):
        for callback in ("sensor_history:S9999", "sensor_chart:S9999", "sensor_chart:bad"):
            await self.dispatch(callback=callback)
            self.assertIn("menu", callback_names(self.last_markup("edit_message_text")))
        self.bot.df = None
        await self.dispatch(callback="sensor_chart:S0001")
        self.assertIn("menu", callback_names(self.last_markup("edit_message_text")))

    async def test_sensor_rendering_preserves_native_location_and_map_links(self):
        self.bot.df["Latitude"] = 41.3
        self.bot.df["Longitude"] = 69.2
        await self.dispatch(text="/sensor 1")
        self.io["send_location"].assert_awaited_once()
        result_buttons = buttons(self.last_markup())
        self.assertEqual(sum(button.url is not None for button in result_buttons), 2)
        self.assertIn("sensor_chart:S0001", callback_names(self.last_markup()))

    def test_polling_creates_and_closes_event_loop_with_existing_ptb(self):
        application = Mock()
        loops = []

        def poll(**kwargs):
            loop = self.bot.asyncio.get_event_loop()
            self.assertFalse(loop.is_closed())
            self.assertEqual(kwargs["allowed_updates"], Update.ALL_TYPES)
            loops.append(loop)

        application.run_polling.side_effect = poll
        self.bot.run_bot_polling(application)
        self.assertTrue(loops[0].is_closed())
        application.run_polling.assert_called_once()

    def test_polling_failure_still_closes_event_loop(self):
        application = Mock()
        loops = []

        def poll(**kwargs):
            loops.append(self.bot.asyncio.get_event_loop())
            raise RuntimeError("offline")

        application.run_polling.side_effect = poll
        with self.assertRaisesRegex(RuntimeError, "offline"):
            self.bot.run_bot_polling(application)
        self.assertTrue(loops[0].is_closed())


    async def test_unavailable_chat_does_not_abort_command_setup(self):
        from telegram.error import BadRequest, Forbidden
        self.bot.load_users.return_value = [self.user_record, {"id": 43, "role": "user"}]
        for error in (BadRequest("Chat not found"), Forbidden("Bot was blocked")):
            with self.subTest(error=type(error).__name__):
                self.io["set_my_commands"].reset_mock()

                async def set_commands(commands, scope):
                    if getattr(scope, "chat_id", None) == 42:
                        raise error

                self.io["set_my_commands"].side_effect = set_commands
                await self.bot.setup_bot_commands(self.app)
                self.assertEqual(self.io["set_my_commands"].await_count, 4)
                chat_ids = {
                    getattr(call.kwargs["scope"], "chat_id", None)
                    for call in self.io["set_my_commands"].await_args_list
                }
                self.assertTrue({42, 43} <= chat_ids)


    def online_weather_response(self):
        return {
            "current": {"time": "2026-10-12T12:15", "temperature_2m": 24.5,
                        "relative_humidity_2m": 22, "wind_speed_10m": 14.7, "precipitation": 0.2},
            "daily": {"time": ["2026-10-12"], "temperature_2m_min": [12],
                      "temperature_2m_max": [25], "wind_speed_10m_max": [19],
                      "relative_humidity_2m_mean": [38], "precipitation_sum": [1.2]},
        }

    async def test_forecast_shows_online_humidity_wind_and_air_dryness(self):
        self.bot.requests = Mock()
        self.bot.requests.get.return_value.json.return_value = self.online_weather_response()
        await self.dispatch(callback="forecast")
        text = self.io["edit_message_text"].await_args.kwargs["text"]
        self.assertIn("Harorat: 24.5°C", text)
        self.assertIn("Havo namligi: 22%", text)
        self.assertIn("Shamol: 14.7 km/soat", text)
        self.assertIn("Havo quruqligi: quruq", text)
        self.assertIn("38%", text)
        self.assertIn("Toshkent vaqti", text)
        self.assertIn("Manba: Open-Meteo", text)
        params = self.bot.requests.get.call_args.kwargs["params"]
        self.assertEqual((params["latitude"], params["longitude"]), (41.3, 69.2))
        self.assertIn("relative_humidity_2m", params["current"])
        self.assertIn("relative_humidity_2m_mean", params["daily"])
        self.assertEqual(params["wind_speed_unit"], "kmh")
        self.bot.requests.get.return_value.raise_for_status.assert_called_once()

    async def test_legacy_weather_uses_same_online_provider_and_location(self):
        self.bot.requests = Mock()
        self.bot.requests.get.return_value.json.return_value = self.online_weather_response()
        await self.dispatch(text="/weather")
        self.assertIn("Havo namligi: 22%", self.sent_text())
        self.assertIn("menu", callback_names(self.last_markup()))
        await self.dispatch(callback="weather")
        self.assertEqual(self.bot.requests.get.call_count, 2)

    def test_weather_location_falls_back_from_invalid_coordinates(self):
        self.user_record.update({"latitude": "bad", "longitude": None})
        self.assertEqual(self.bot.weather_location(self.update(text="/weather")), (41.3, 69.2, "Chilonzor"))
        self.user_record["district"] = ""
        self.assertEqual(self.bot.weather_location(self.update(text="/weather")), (41.3111, 69.2797, "Toshkent"))
        self.user_record.update({"latitude": float("nan"), "longitude": 69.2})
        self.assertEqual(self.bot.weather_location(self.update(text="/weather"))[2], "Toshkent")

    def test_air_dryness_is_based_on_relative_humidity_without_fake_percentage(self):
        for humidity, expected in ((0, "quruq"), (29, "quruq"), (30, "o'rtacha"),
                                   (60, "o'rtacha"), (61, "nam"), (100, "nam"),
                                   (None, "ma'lumot yo'q"), (float("nan"), "ma'lumot yo'q"),
                                   (-1, "ma'lumot yo'q"), (101, "ma'lumot yo'q")):
            self.assertEqual(self.bot.air_dryness(humidity), expected)

    async def test_online_weather_failure_and_missing_values_do_not_use_sensor_data(self):
        from requests import RequestException
        self.bot.requests = Mock()
        self.bot.requests.get.side_effect = RequestException("offline")
        await self.dispatch(callback="forecast")
        self.assertIn("Internetdan ob-havo olinmadi", self.sent_text())
        self.assertNotIn("Harorat: 25", self.sent_text())
        self.assertIn("menu", callback_names(self.last_markup("edit_message_text")))
        self.bot.requests.get.side_effect = None
        self.bot.requests.get.return_value.json.return_value = {"current": {"time": "2026-10-12T12:15"}}
        await self.dispatch(callback="forecast")
        text = self.io["edit_message_text"].await_args.kwargs["text"]
        self.assertIn("Havo namligi: ma'lumot yo'q", text)
        self.assertIn("Havo quruqligi: ma'lumot yo'q", text)
        self.assertNotIn("50%", text)
        self.bot.requests.get.return_value.json.return_value = {"current": {}, "daily": {"time": ["2026-10-12"], "temperature_2m_min": []}}
        await self.dispatch(callback="forecast")
        self.assertIn("ma'lumot yo'q", self.io["edit_message_text"].await_args.kwargs["text"])

    async def test_online_weather_rejects_http_and_api_errors(self):
        from requests import RequestException
        self.bot.requests = Mock()
        self.bot.requests.get.return_value.raise_for_status.side_effect = RequestException("HTTP 503")
        await self.dispatch(callback="forecast")
        self.bot.requests.get.return_value.json.assert_not_called()
        self.bot.requests.get.return_value.raise_for_status.side_effect = None
        for response in ({"error": True, "reason": "bad request"}, [], {}):
            self.bot.requests.get.return_value.json.return_value = response
            await self.dispatch(callback="forecast")
            self.assertIn("Internetdan ob-havo olinmadi", self.io["edit_message_text"].await_args.kwargs["text"])


if __name__ == "__main__":
    unittest.main()
