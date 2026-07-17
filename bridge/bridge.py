from models.bot_factory import create_bot
from bridge.context import Context
from bridge.reply import Reply
from common import const
from common.log import logger
from common.singleton import singleton
from config import conf
try:
    from translate.factory import create_translator
except ImportError:
    create_translator = None


@singleton
class Bridge(object):
    def __init__(self):
        self.btype = {
            "chat": const.OPENAI,
            "translate": "baidu",
        }
        # Resolve bot type from model
        bot_type = conf().get("bot_type")
        if bot_type:
            self.btype["chat"] = bot_type
        else:
            model_type = conf().get("model") or const.GPT_41_MINI

            # Ensure model_type is string to prevent AttributeError when using startswith()
            if not isinstance(model_type, str):
                logger.warning(f"[Bridge] model_type is not a string: {model_type} (type: {type(model_type).__name__}), converting to string")
                model_type = str(model_type)

            if conf().get("use_azure_chatgpt", False):
                self.btype["chat"] = const.CHATGPTONAZURE
            if model_type in [const.QWEN, const.QWEN_TURBO, const.QWEN_PLUS, const.QWEN_MAX]:
                self.btype["chat"] = const.QWEN_DASHSCOPE
            if model_type and (model_type.startswith("qwen") or model_type.startswith("qwq") or model_type.startswith("qvq")):
                self.btype["chat"] = const.QWEN_DASHSCOPE
            if model_type and model_type.startswith("deepseek"):
                self.btype["chat"] = const.DEEPSEEK

        self.bots = {}
        self.chat_bots = {}
        self._agent_bridge = None

    # 模型对应的接口
    def get_bot(self, typename):
        if self.bots.get(typename) is None:
            logger.info("create bot {} for {}".format(self.btype[typename], typename))
            if typename == "chat":
                self.bots[typename] = create_bot(self.btype[typename])
            elif typename == "translate":
                if create_translator is None:
                    raise RuntimeError("translate module not available")
                self.bots[typename] = create_translator(self.btype[typename])
        return self.bots[typename]

    def get_bot_type(self, typename):
        return self.btype[typename]

    def fetch_reply_content(self, query, context: Context) -> Reply:
        return self.get_bot("chat").reply(query, context)

    def fetch_translate(self, text, from_lang="", to_lang="en") -> Reply:
        return self.get_bot("translate").translate(text, from_lang, to_lang)

    def find_chat_bot(self, bot_type: str):
        if self.chat_bots.get(bot_type) is None:
            self.chat_bots[bot_type] = create_bot(bot_type)
        return self.chat_bots.get(bot_type)

    def reset_bot(self):
        """
        重置bot路由
        """
        self.__init__()

    def get_agent_bridge(self):
        """
        Get agent bridge for agent-based conversations
        """
        if self._agent_bridge is None:
            from bridge.agent_bridge import AgentBridge
            self._agent_bridge = AgentBridge(self)
        return self._agent_bridge

    def fetch_agent_reply(self, query: str, context: Context = None,
                          on_event=None, clear_history: bool = False) -> Reply:
        """
        Use super agent to handle the query

        Args:
            query: User query
            context: Context object
            on_event: Event callback for streaming
            clear_history: Whether to clear conversation history

        Returns:
            Reply object
        """
        agent_bridge = self.get_agent_bridge()
        return agent_bridge.agent_reply(query, context, on_event, clear_history)
