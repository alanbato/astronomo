"""Compose/reply modal for GMAP mail."""

import logging

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, TextArea

from astronomo.gmap_accounts import GmapAccount
from astronomo.identities import IdentityManager
from astronomo.mail_cache import CachedMessage

logger = logging.getLogger(__name__)


class ComposeModal(ModalScreen[bool]):
    """Modal for composing or replying to mail.

    Returns True if message was sent, False/None if cancelled.
    """

    DEFAULT_CSS = """
    ComposeModal {
        align: center middle;
    }

    ComposeModal > Container {
        width: 85;
        height: 80%;
        border: thick $primary;
        border-title-align: center;
        background: $surface;
        padding: 1 2;
    }

    ComposeModal .field-label {
        margin-top: 1;
    }

    ComposeModal Input {
        width: 100%;
    }

    ComposeModal TextArea {
        width: 100%;
        height: 1fr;
        min-height: 10;
    }

    ComposeModal .button-row {
        align: center middle;
        padding-top: 1;
    }

    ComposeModal .sending-message {
        text-align: center;
        color: $text-muted;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(
        self,
        account: GmapAccount,
        identity_manager: IdentityManager,
        reply_to: CachedMessage | None = None,
        to: str = "",
        subject: str = "",
        body: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.account = account
        self.identity_manager = identity_manager
        self.reply_to = reply_to
        self.initial_to = to
        self.initial_subject = subject
        self.initial_body = body

    def compose(self) -> ComposeResult:
        is_reply = self.reply_to is not None
        title = "Reply" if is_reply else "Compose"

        container = Container()
        container.border_title = title
        with container:
            # From (read-only display)
            from_addr = f"{self.account.mailbox}@{self.account.hostname}"
            yield Label(f"From: {from_addr}", classes="field-label")

            # To
            yield Label("To:", classes="field-label")
            to_value = self.initial_to
            if is_reply and self.reply_to:
                try:
                    msg = self.reply_to.parse()
                    if msg.senders:
                        to_value = msg.senders[0].address
                except (ValueError, IndexError):
                    pass
            yield Input(value=to_value, placeholder="user@hostname", id="to-input")

            # Subject
            yield Label("Subject:", classes="field-label")
            subject_value = self.initial_subject
            if is_reply and self.reply_to and self.reply_to.subject:
                if not self.reply_to.subject.startswith("Re:"):
                    subject_value = f"Re: {self.reply_to.subject}"
                else:
                    subject_value = self.reply_to.subject
            yield Input(value=subject_value, id="subject-input")

            # Body
            yield Label("Message (gemtext):", classes="field-label")
            body_value = self.initial_body
            if is_reply and self.reply_to:
                try:
                    msg = self.reply_to.parse()
                    # Quote original message
                    quoted_lines = [f"> {line}" for line in msg.body.split("\n")]
                    body_value = "\n\n" + "\n".join(quoted_lines)
                except (ValueError, IndexError):
                    pass
            yield TextArea(body_value, id="body-input")

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Send", variant="primary", id="send-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "send-btn":
            self._send_message()

    @work(exclusive=True)
    async def _send_message(self) -> None:
        """Send the composed message."""
        to = self.query_one("#to-input", Input).value.strip()
        subject = self.query_one("#subject-input", Input).value.strip()
        body = self.query_one("#body-input", TextArea).text

        if not to:
            self.app.notify("Recipient is required", severity="error")
            return

        # Validate Misfin address format: mailbox@hostname
        parts = to.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1] or "." not in parts[1]:
            self.app.notify(
                "Invalid address format (use user@hostname.tld)", severity="error"
            )
            return

        from titlani.client.session import MisfinClient
        from titlani.content.gemmail import MisfinAddress

        # Get identity for sending
        identity = self.identity_manager.get_identity(self.account.identity_id)
        if identity is None:
            self.app.notify("Identity not found", severity="error")
            return

        sender = MisfinAddress(
            mailbox=self.account.mailbox,
            hostname=self.account.hostname,
        )

        # Disable send button
        send_btn = self.query_one("#send-btn", Button)
        send_btn.disabled = True
        send_btn.label = "Sending..."

        try:
            # Send to recipient via Misfin
            async with MisfinClient(
                client_cert=identity.cert_path,
                client_key=identity.key_path,
            ) as client:
                response = await client.send(
                    to=to,
                    body=body,
                    subject=subject or None,
                    sender=sender,
                )

            if not (20 <= response.status < 30):
                self.app.notify(f"Delivery failed: {response.meta}", severity="error")
                send_btn.disabled = False
                send_btn.label = "Send"
                return

            # Send copy to GMAP address for Sent folder
            gmap_address = self.account.gmap_address
            if gmap_address:
                try:
                    async with MisfinClient(
                        client_cert=identity.cert_path,
                        client_key=identity.key_path,
                    ) as client:
                        await client.send(
                            to=gmap_address,
                            body=body,
                            subject=subject or None,
                            sender=sender,
                        )
                except Exception as e:
                    logger.warning("Failed to save to Sent: %s", e)
                    self.app.notify(
                        "Message sent, but Sent copy failed", severity="warning"
                    )

            self.dismiss(True)

        except Exception as e:
            logger.exception("Failed to send message")
            self.app.notify(f"Send failed: {e}", severity="error")
            send_btn.disabled = False
            send_btn.label = "Send"

    def action_cancel(self) -> None:
        self.dismiss(None)
