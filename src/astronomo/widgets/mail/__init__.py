"""Mail widgets for Astronomo."""

from astronomo.widgets.mail.add_account_modal import AddAccountModal
from astronomo.widgets.mail.compose_modal import ComposeModal
from astronomo.widgets.mail.confirm_delete_modal import ConfirmDeleteMailModal
from astronomo.widgets.mail.message_list_panel import MessageListPanel
from astronomo.widgets.mail.message_preview_panel import MessagePreviewPanel
from astronomo.widgets.mail.tag_list_panel import TagListPanel
from astronomo.widgets.mail.tag_manage_modal import TagManageModal

__all__ = [
    "AddAccountModal",
    "ComposeModal",
    "ConfirmDeleteMailModal",
    "MessageListPanel",
    "MessagePreviewPanel",
    "TagListPanel",
    "TagManageModal",
]
