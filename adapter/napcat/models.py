from pydantic import BaseModel, Field


class Sender(BaseModel):
    user_id: int
    nickname: str = ""


class GroupMessage(BaseModel):
    post_type: str = Field("message")  # 固定值
    message_type: str = Field("group")  # 群聊
    sub_type: str = "normal"
    group_id: int
    user_id: int
    sender: Sender
    raw_message: str
