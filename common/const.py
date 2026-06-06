# Provider types
OPENAI = "openai"
CHATGPT = "chatGPT"  # legacy alias for OPENAI, kept for backward compatibility
CHATGPTONAZURE = "chatGPTOnAzure"
QWEN = "qwen"  # legacy alias, actually routed to DashscopeBot
QWEN_DASHSCOPE = "dashscope"  # Qwen via DashScope
DEEPSEEK = "deepseek"
CUSTOM = "custom"  # custom OpenAI-compatible API, bot_type won't auto-switch on model change

# OpenAI models
GPT35 = "gpt-3.5-turbo"
GPT35_0125 = "gpt-3.5-turbo-0125"
GPT35_1106 = "gpt-3.5-turbo-1106"
GPT4 = "gpt-4"
GPT4_06_13 = "gpt-4-0613"
GPT4_32k = "gpt-4-32k"
GPT4_32k_06_13 = "gpt-4-32k-0613"
GPT4_TURBO = "gpt-4-turbo"
GPT4_TURBO_PREVIEW = "gpt-4-turbo-preview"
GPT4_TURBO_01_25 = "gpt-4-0125-preview"
GPT4_TURBO_11_06 = "gpt-4-1106-preview"
GPT4_TURBO_04_09 = "gpt-4-turbo-2024-04-09"
GPT4_VISION_PREVIEW = "gpt-4-vision-preview"
GPT_4o = "gpt-4o"
GPT_4O_0806 = "gpt-4o-2024-08-06"
GPT_4o_MINI = "gpt-4o-mini"
GPT_41 = "gpt-4.1"
GPT_41_MINI = "gpt-4.1-mini"
GPT_41_NANO = "gpt-4.1-nano"
GPT_5 = "gpt-5"
GPT_5_MINI = "gpt-5-mini"
GPT_5_NANO = "gpt-5-nano"
GPT_54 = "gpt-5.4"
GPT_54_MINI = "gpt-5.4-mini"
GPT_54_NANO = "gpt-5.4-nano"
GPT_55 = "gpt-5.5"
GPT_56_LUNA = "gpt-5.6-luna"
GPT_56_TERRA = "gpt-5.6-terra"
GPT_56_SOL = "gpt-5.6-sol"
O1 = "o1-preview"
O1_MINI = "o1-mini"
# DeepSeek models
DEEPSEEK_CHAT = "deepseek-chat"
DEEPSEEK_REASONER = "deepseek-reasoner"
DEEPSEEK_V4_FLASH = "deepseek-v4-flash"
DEEPSEEK_V4_PRO = "deepseek-v4-pro"

# Qwen (Alibaba Cloud DashScope)
QWEN_TURBO = "qwen-turbo"
QWEN_PLUS = "qwen-plus"
QWEN_MAX = "qwen-max"
QWEN_LONG = "qwen-long"
QWEN3_MAX = "qwen3-max"
QWEN35_PLUS = "qwen3.5-plus"
QWEN36_PLUS = "qwen3.6-plus"
QWEN37_PLUS = "qwen3.7-plus"
QWEN37_MAX = "qwen3.7-max"
QWQ_PLUS = "qwq-plus"

MODEL_LIST = [
    # DeepSeek
    DEEPSEEK_V4_FLASH, DEEPSEEK_V4_PRO, DEEPSEEK_CHAT, DEEPSEEK_REASONER,

    # OpenAI
    GPT35, GPT35_0125, GPT35_1106, "gpt-3.5-turbo-16k",
    GPT4, GPT4_06_13, GPT4_32k, GPT4_32k_06_13,
    GPT4_TURBO, GPT4_TURBO_PREVIEW, GPT4_TURBO_01_25, GPT4_TURBO_11_06, GPT4_TURBO_04_09,
    GPT_4o, GPT_4O_0806, GPT_4o_MINI,
    GPT_41, GPT_41_MINI, GPT_41_NANO,
    GPT_56_LUNA, GPT_56_TERRA, GPT_56_SOL,
    GPT_5, GPT_5_MINI, GPT_5_NANO,
    GPT_54, GPT_55, GPT_54_MINI, GPT_54_NANO,
    O1, O1_MINI,

    # Qwen
    QWEN37_PLUS, QWEN37_MAX, QWEN36_PLUS, QWEN35_PLUS, QWEN3_MAX, QWEN_MAX, QWEN_PLUS, QWEN_TURBO, QWEN_LONG,
]

# channel
FEISHU = "feishu"
