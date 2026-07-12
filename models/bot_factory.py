"""
channel factory
"""
from common import const


def create_bot(bot_type):
    """
    create a bot_type instance
    :param bot_type: bot type code
    :return: bot instance
    """
    if bot_type == const.DEEPSEEK:
        from models.deepseek.deepseek_bot import DeepSeekBot
        return DeepSeekBot()

    elif bot_type in (const.OPENAI, const.CHATGPT, const.CUSTOM) or bot_type.startswith("custom:"):
        from models.chatgpt.chat_gpt_bot import ChatGPTBot
        return ChatGPTBot()

    elif bot_type == const.CHATGPTONAZURE:
        from models.chatgpt.chat_gpt_bot import AzureChatGPTBot
        return AzureChatGPTBot()

    elif bot_type in (const.QWEN, const.QWEN_DASHSCOPE):
        from models.dashscope.dashscope_bot import DashscopeBot
        return DashscopeBot()

    raise RuntimeError(f"unsupported bot type: {bot_type}")
