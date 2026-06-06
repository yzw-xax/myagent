# encoding:utf-8

import ast
import copy
import json
import logging
import os
import pickle
import sys

from common.log import logger
from common import i18n

# All available config keys are listed in this dict (use lowercase keys).
# The values here are placeholders only; the program does NOT read them.
# They merely document the expected format — put real values in config.json.
available_setting = {
    # OpenAI / OpenAI-compatible API config
    "open_ai_api_key": "",
    "open_ai_api_base": "https://api.openai.com/v1",
    "custom_api_key": "",  # custom OpenAI-compatible provider api key (used when bot_type is "custom"); legacy single-provider field
    "custom_api_base": "",  # custom OpenAI-compatible provider api base (used when bot_type is "custom"); legacy single-provider field
    # Multiple custom (OpenAI-compatible) providers. Activated via bot_type: "custom:<id>".
    # Each item: {"id": "3f2a9c1b", "name": "my-provider", "api_key": "sk-...", "api_base": "https://api.example.com/v1", "model": "model-name"}
    "custom_providers": [],
    "proxy": "",  # proxy used by openai
    # Model selection
    "model": "gpt-3.5-turbo",  # options: deepseek-v4-flash, deepseek-v4-pro, gpt-4o, qwen-turbo, qwen-plus, qwen-max, etc. See common/const.py for the full list
    "bot_type": "",  # optional; for OpenAI-compatible third-party services set "openai" or "custom" (in custom mode switching model won't auto-switch bot_type). See common/const.py for bot names; inferred from model name if left empty
    # Azure OpenAI config
    "use_azure_chatgpt": False,
    "azure_deployment_id": "",
    "azure_api_version": "",
    # DeepSeek config
    "deepseek_api_key": "",
    "deepseek_api_base": "https://api.deepseek.com/v1",
    # DashScope (Qwen) config
    "dashscope_api_key": "",
    # Embedding model config
    "embedding_provider": "",  # explicitly set the provider: openai / dashscope (aligned with bot_type naming)
    "embedding_model": "",     # leave empty to use the provider's default model
    "embedding_dimensions": 0, # leave empty/0 to use the provider's default dimension (1024 recommended for consistency)
    # Bot trigger config
    "single_chat_prefix": ["bot", "@bot"],
    "single_chat_reply_prefix": "[bot] ",
    "single_chat_reply_suffix": "",
    "group_chat_prefix": ["@bot"],
    "no_need_at": False,
    "group_chat_reply_prefix": "",
    "group_chat_reply_suffix": "",
    "group_chat_keyword": [],
    "group_at_off": False,
    "group_name_white_list": ["group1", "group2"],
    "group_name_keyword_white_list": [],
    "group_chat_in_one_session": ["group1"],
    "group_shared_session": False,
    "nick_name_black_list": [],
    "group_welcome_msg": "",
    "trigger_by_self": False,
    # Image generation config
    "text_to_image": "dall-e-2",  # image generation model, options: dall-e-2, dall-e-3
    "dalle3_image_style": "vivid",
    "dalle3_image_quality": "hd",
    # Azure OpenAI DALL-E API config; when use_azure_chatgpt is true
    "azure_openai_dalle_api_base": "",
    "azure_openai_dalle_api_key": "",
    "azure_openai_dalle_deployment_id": "",
    "image_proxy": True,
    "image_create_prefix": ["画", "看", "找"],
    "image_create_size": "256x256",
    "concurrency_in_session": 1,
    "group_chat_exit_group": False,
    # Session params
    "expires_in_seconds": 3600,
    "character_desc": "You are a helpful AI assistant. You aim to answer and solve any questions people have, and can communicate in multiple languages.",
    "conversation_max_tokens": 1000,
    # Rate limit
    "rate_limit_chatgpt": 20,
    "rate_limit_dalle": 50,
    # API params, see https://platform.openai.com/docs/api-reference/chat/create
    "temperature": 0.9,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "request_timeout": 180,
    "timeout": 120,
    # service time limit
    "chat_time_module": False,
    "chat_start_time": "00:00",
    "chat_stop_time": "24:00",
    # Custom trigger words for chatgpt commands
    "clear_memory_commands": ["#清除记忆"],
    # Channel config
    "channel_type": "",  # options: web, feishu (or both: "web, feishu")
    "web_console": True,
    "subscribe_msg": "",
    "debug": False,
    "appdata_dir": "",
    # Plugin config
    "plugin_trigger_prefix": "$",
    "use_global_plugin_config": False,
    "max_media_send_count": 3,
    "media_send_interval": 1,
    # Feishu config
    "feishu_port": 80,
    "feishu_app_id": "",
    "feishu_app_secret": "",
    "feishu_token": "",
    "feishu_event_mode": "websocket",
    "feishu_stream_reply": True,
    "feishu_detailed_card": True,
    # Web console config
    "web_host": "",
    "web_port": 9899,
    "web_password": "",
    "web_session_expire_days": 30,
    "web_file_serve_root": "~",
    # Agent mode config
    "agent": True,
    "agent_workspace": "~/myclaw",
    "agent_max_context_tokens": 64000,
    "agent_max_context_turns": 30,
    "agent_max_steps": 30,
    "enable_thinking": False,
    "reasoning_effort": "high",
    # Knowledge base & self-evolution
    "knowledge": True,
    "self_evolution_enabled": False,
    "self_evolution_idle_minutes": 10,
    "self_evolution_min_turns": 6,
    "deep_dream_enabled": True,
    # Skills
    "skill": {},
}


class Config(dict):
    def __init__(self, d=None):
        super().__init__()
        if d is None:
            d = {}
        for k, v in d.items():
            self[k] = v
        # user_datas: per-user data; key is the username, value is the user's data (also a dict)
        self.user_datas = {}

    def __getitem__(self, key):
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        return super().__setitem__(key, value)

    def get(self, key, default=None):
        # skip comment fields starting with an underscore
        if key.startswith("_"):
            return super().get(key, default)
        
        # if the key is not in available_setting, fall back to dict.get and return the value actually loaded from config.json (or default if absent)
        if key not in available_setting:
            return super().get(key, default)
        
        try:
            return self[key]
        except KeyError as e:
            return default
        except Exception as e:
            raise e

    # Make sure to return a dictionary to ensure atomic
    def get_user_data(self, user) -> dict:
        if self.user_datas.get(user) is None:
            self.user_datas[user] = {}
        return self.user_datas[user]

    # SECURITY NOTE: pickle.load() can execute arbitrary code during
    # deserialization. This is safe as long as user_datas.pkl is trusted
    # (local app data directory, written only by this process). For a future
    # hardening pass, consider migrating to JSON (json.load/json.dump) if the
    # data structures are JSON-serializable, or adding an HMAC signature to
    # detect tampering of the pickle file.
    def load_user_datas(self):
        try:
            with open(os.path.join(get_appdata_dir(), "user_datas.pkl"), "rb") as f:
                self.user_datas = pickle.load(f)
                logger.debug("[Config] User datas loaded.")
        except FileNotFoundError as e:
            logger.debug("[Config] User datas file not found, ignore.")
        except Exception as e:
            logger.warning("[Config] User datas error: {}".format(e))
            self.user_datas = {}

    def save_user_datas(self):
        try:
            # SECURITY: pickle.dump output should only be loaded by this same
            # process. See note on load_user_datas() above.
            with open(os.path.join(get_appdata_dir(), "user_datas.pkl"), "wb") as f:
                pickle.dump(self.user_datas, f)
                logger.info("[Config] User datas saved.")
        except Exception as e:
            logger.info("[Config] User datas error: {}".format(e))


config = Config()


def _mask_value(val):
    """Mask a sensitive string value, keeping first 3 and last 3 chars."""
    if not isinstance(val, str) or len(val) <= 8:
        return val
    return val[0:3] + "*" * 5 + val[-3:]


def _mask_sensitive_recursive(obj):
    """Recursively mask values whose keys contain 'key' or 'secret'."""
    if isinstance(obj, dict):
        masked = {}
        for k, v in obj.items():
            if ("key" in k or "secret" in k) and isinstance(v, str):
                masked[k] = _mask_value(v)
            else:
                masked[k] = _mask_sensitive_recursive(v)
        return masked
    elif isinstance(obj, list):
        return [_mask_sensitive_recursive(item) for item in obj]
    return obj


def drag_sensitive(config):
    try:
        if isinstance(config, str):
            conf_dict: dict = json.loads(config)
            conf_dict_copy = _mask_sensitive_recursive(conf_dict)
            return json.dumps(conf_dict_copy, indent=4)

        elif isinstance(config, dict):
            return _mask_sensitive_recursive(config)
    except Exception as e:
        logger.exception(e)
        return config
    return config


def load_config():
    global config

    # print ASCII logo
    logger.info("  __  __            _                    ")
    logger.info(" |  \/  |_   _  ___| | ___ __ ___   __ _ ")
    logger.info(" | |\/| | | | |/ __| |/ / '_ ` _ \ / _` |")
    logger.info(" | |  | | |_| | (__|   <| | | | | | (_| |")
    logger.info(" |_|  |_|\__, |\___|_|\_\_| |_| |_|\__,_|")
    logger.info("         |___/                            ")
    logger.info("")
    # User config lives in the data root: source deployments use CWD (./), while
    # the desktop build points MYCLAW_DATA_DIR at ~/.myclaw so config survives updates.
    config_path = os.path.join(get_data_root(), "config.json")
    if not os.path.exists(config_path):
        logger.info("config file not found, falling back to config-template.json")
        # Resolve the template via get_resource_root() so it works both from
        # source and from a frozen (PyInstaller) bundle, where the template
        # ships inside the bundle (sys._MEIPASS) and CWD may differ.
        template_path = os.path.join(get_resource_root(), "config-template.json")
        config_path = template_path if os.path.exists(template_path) else "./config-template.json"

    config_str = read_file(config_path)
    logger.debug("[INIT] config str: {}".format(drag_sensitive(config_str)))

    # Deserialize the json string into a dict.
    # `object_pairs_hook` lets us catch users who accidentally typed the
    # same key twice (e.g. two `"tools"` blocks) — json.loads would
    # otherwise silently drop all but the last occurrence.
    config = Config(json.loads(config_str, object_pairs_hook=_merge_duplicate_keys))

    # Migrate legacy singular keys (`tool`, `skill`) into the canonical
    # plural buckets so the rest of the codebase only reads one schema.
    # Deep-merge so existing `tools`/`skills` entries are preserved and
    # only missing namespaces are filled in from the legacy section.
    _merge_legacy_namespace(config, legacy="tool",  canonical="tools")
    _merge_legacy_namespace(config, legacy="skill", canonical="skills")

    # override config with environment variables.
    # Some online deployment platforms (e.g. Railway) deploy project from github directly. So you shouldn't put your secrets like api key in a config file, instead use environment variables to override the default config.
    for name, value in os.environ.items():
        name = name.lower()
        # skip comment fields starting with an underscore
        if name.startswith("_"):
            continue
        if name in available_setting:
            logger.info("[INIT] override config by environ args: {}={}".format(name, value))
            try:
                # SECURITY: Use ast.literal_eval instead of eval().
                # ast.literal_eval only parses Python literals (strings, numbers,
                # tuples, lists, dicts, booleans, None) and CANNOT execute
                # arbitrary code, preventing environment-variable injection.
                config[name] = ast.literal_eval(value)
            except Exception:
                # literal_eval can raise ValueError/SyntaxError for non-literal
                # strings, but also TypeError/RecursionError on malformed input
                # (e.g. unhashable dict keys); catch broadly to avoid crashing
                # startup, and fall back to treating the value as a plain string.
                if value.lower() == "false":
                    config[name] = False
                elif value.lower() == "true":
                    config[name] = True
                else:
                    config[name] = value

    if config.get("debug", False):
        logger.setLevel(logging.DEBUG)
        logger.debug("[INIT] set log level to DEBUG")

    # Resolve the global UI language as early as possible so that every
    # downstream layer (logs, CLI, agent prompts, channel replies) shares it.
    resolved_lang = i18n.resolve_language(config.get("myclaw_lang", "auto"))

    logger.info("[INIT] load config: {}".format(drag_sensitive(config)))

    # print system initialization info
    logger.info("[INIT] ========================================")
    logger.info("[INIT] System Initialization")
    logger.info("[INIT] ========================================")
    logger.info("[INIT] Language: {}".format(resolved_lang))
    logger.info("[INIT] Channel: {}".format(config.get("channel_type", "unknown")))
    logger.info("[INIT] Model: {}".format(config.get("model", "unknown")))

    # Agent mode info
    if config.get("agent", True):
        workspace = config.get("agent_workspace", "~/myclaw")
        logger.info("[INIT] Mode: Agent (workspace: {})".format(workspace))
    else:
        logger.info("[INIT] Mode: Chat (set \"agent\":true in config.json to enable Agent mode)")

    logger.info("[INIT] Debug: {}".format(config.get("debug", False)))
    logger.info("[INIT] ========================================")

    # Sync selected config values to environment variables so that
    # subprocesses (e.g. shell skill scripts) can access them directly.
    # Existing env vars are NOT overwritten (env takes precedence).
    _CONFIG_TO_ENV = {
        "open_ai_api_key": "OPENAI_API_KEY",
        "open_ai_api_base": "OPENAI_API_BASE",
        "deepseek_api_key": "DEEPSEEK_API_KEY",
        "deepseek_api_base": "DEEPSEEK_API_BASE",
        "dashscope_api_key": "DASHSCOPE_API_KEY",
        # Channel credentials (used by skills that check env vars)
        "feishu_app_id": "FEISHU_APP_ID",
        "feishu_app_secret": "FEISHU_APP_SECRET",
    }
    injected = 0
    for conf_key, env_key in _CONFIG_TO_ENV.items():
        if env_key not in os.environ:
            val = config.get(conf_key, "")
            if val:
                os.environ[env_key] = str(val)
                injected += 1

    injected += _sync_skill_config_to_env(config.get("skills", {}))

    if injected:
        logger.info("[INIT] Synced {} config values to environment variables".format(injected))

    config.load_user_datas()


def _deep_merge_dicts(base: dict, incoming: dict) -> dict:
    """Recursively merge ``incoming`` into ``base`` (incoming wins on leaves)."""
    for key, val in incoming.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(val, dict)
        ):
            _deep_merge_dicts(base[key], val)
        else:
            base[key] = val
    return base


def _merge_duplicate_keys(pairs):
    """object_pairs_hook for json.loads: deep-merge duplicate top-level keys
    (lists concat, dicts merge, scalars take the latter) instead of dropping."""
    out = {}
    duplicates = []
    for key, val in pairs:
        if key not in out:
            out[key] = val
            continue
        duplicates.append(key)
        prev = out[key]
        if isinstance(prev, dict) and isinstance(val, dict):
            _deep_merge_dicts(prev, val)
        elif isinstance(prev, list) and isinstance(val, list):
            prev.extend(val)
        else:
            out[key] = val
    if duplicates:
        # logger may not be wired yet — fall back to print so we never lose the warning.
        unique = sorted(set(duplicates))
        try:
            logger.warning("[INIT] config.json has duplicate keys (merged): %s", unique)
        except Exception:
            print("[INIT] config.json has duplicate keys (merged):", unique)
    return out


def _merge_legacy_namespace(cfg, legacy: str, canonical: str) -> None:
    """Fold deprecated singular keys (``tool`` / ``skill``) into their plural
    canonical counterparts at load time. Canonical entries always win."""
    legacy_section = cfg.get(legacy)
    if not isinstance(legacy_section, dict) or not legacy_section:
        cfg.pop(legacy, None)
        return
    canonical_section = cfg.get(canonical)
    if not isinstance(canonical_section, dict):
        canonical_section = {}
    merged_keys = []
    for name, val in legacy_section.items():
        if name in canonical_section:
            if isinstance(canonical_section[name], dict) and isinstance(val, dict):
                for sub_key, sub_val in val.items():
                    if (
                        sub_key in canonical_section[name]
                        and isinstance(canonical_section[name][sub_key], dict)
                        and isinstance(sub_val, dict)
                    ):
                        _deep_merge_dicts(sub_val, canonical_section[name][sub_key])
                        canonical_section[name][sub_key] = sub_val
                    else:
                        canonical_section[name].setdefault(sub_key, sub_val)
            continue
        canonical_section[name] = val
        merged_keys.append(name)
    cfg[canonical] = canonical_section
    cfg.pop(legacy, None)
    if merged_keys:
        logger.warning(
            "[INIT] Legacy config key '{}' is deprecated; merged into '{}': {}. "
            "Please rename '{}' to '{}' in your config.json.".format(
                legacy, canonical, merged_keys, legacy, canonical,
            )
        )


def _sync_skill_config_to_env(skill_section) -> int:
    """Flatten skill-namespaced config into environment variables.

    Mapping rule: ``config["skills"][<name>][<key>]`` -> ``SKILL_<NAME>_<KEY>``
    (e.g. ``skills["image-generation"].model`` -> ``SKILL_IMAGE_GENERATION_MODEL``).

    This lets subprocess-based skill scripts read their own settings without
    importing project code. Existing env vars are NOT overwritten so the
    real environment always wins.

    Returns the number of variables actually injected.
    """
    if not isinstance(skill_section, dict):
        return 0
    injected = 0
    for skill_name, skill_conf in skill_section.items():
        if not isinstance(skill_conf, dict):
            continue
        name_part = str(skill_name).replace("-", "_").upper()
        for key, val in skill_conf.items():
            if val is None or val == "":
                continue
            env_key = "SKILL_{}_{}".format(name_part, str(key).upper())
            if env_key in os.environ:
                continue
            os.environ[env_key] = str(val)
            injected += 1
    return injected


def get_root():
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_root():
    """Directory holding bundled read-only resources (e.g. config-template.json).

    Under PyInstaller, data files live in sys._MEIPASS (the onedir _internal
    folder), which differs from get_root() — the latter is used for writable
    user data and should stay next to the executable, not inside the bundle.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_data_root():
    """Directory for writable user data (config.json, user_datas.pkl, run.log).

    The desktop build sets MYCLAW_DATA_DIR (e.g. ~/.myclaw) so data lives in the
    user's home rather than inside the read-only app bundle and survives app
    updates. When unset (source deployment), it falls back to get_root(), so
    existing behavior is unchanged.
    """
    data_dir = os.environ.get("MYCLAW_DATA_DIR")
    if data_dir:
        data_dir = os.path.expanduser(data_dir)
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    return get_root()


def read_file(path):
    with open(path, mode="r", encoding="utf-8-sig") as f:
        return f.read()


def conf():
    return config


def get_appdata_dir():
    data_path = os.path.join(get_data_root(), conf().get("appdata_dir", ""))
    if not os.path.exists(data_path):
        logger.info("[INIT] data path not exists, create it: {}".format(data_path))
        os.makedirs(data_path)
    return data_path


def get_weixin_credentials_path():
    """Resolve the Weixin credentials (token) file path.

    Honors an explicit ``weixin_credentials_path`` from config. Otherwise the
    packaged desktop build (MYCLAW_DATA_DIR set) keeps it under the data dir
    (~/.myclaw) so all user data stays together, while source deployments retain
    the legacy ~/.weixin_myclaw_credentials.json default unchanged.
    """
    configured = conf().get("weixin_credentials_path")
    if configured:
        return os.path.expanduser(configured)
    if os.environ.get("MYCLAW_DATA_DIR"):
        return os.path.join(get_data_root(), "weixin_credentials.json")
    return os.path.expanduser("~/.weixin_myclaw_credentials.json")


def subscribe_msg():
    trigger_prefix = conf().get("single_chat_prefix", [""])[0]
    msg = conf().get("subscribe_msg", "")
    return msg.format(trigger_prefix=trigger_prefix)


# global plugin config
plugin_config = {}


def write_plugin_config(pconf: dict):
    """
    Write the global plugin config.
    :param pconf: the full plugin config
    """
    global plugin_config
    for k in pconf:
        plugin_config[k.lower()] = pconf[k]

def remove_plugin_config(name: str):
    """
    Remove the global config of a plugin pending reload.
    :param name: name of the plugin to reload
    """
    global plugin_config
    plugin_config.pop(name.lower(), None)


def pconf(plugin_name: str) -> dict:
    """
    Get the config for a plugin by name.
    :param plugin_name: plugin name
    :return: the plugin's config
    """
    return plugin_config.get(plugin_name.lower())


# global config holding globally-effective state
global_config = {"admin_users": []}
