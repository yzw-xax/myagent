"""
channel factory
"""
from common import const
from .channel import Channel


def create_channel(channel_type) -> Channel:
    """
    create a channel instance
    :param channel_type: channel type code
    :return: channel instance
    """
    ch = Channel()
    if channel_type == 'web':
        from channel.web.web_channel import WebChannel
        ch = WebChannel()
    elif channel_type == const.FEISHU:
        from channel.feishu.feishu_channel import FeiShuChanel
        ch = FeiShuChanel()
    else:
        raise RuntimeError(f"unsupported channel type: {channel_type}")
    ch.channel_type = channel_type
    return ch
