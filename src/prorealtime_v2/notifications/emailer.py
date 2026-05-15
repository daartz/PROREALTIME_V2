"""Envoi email sans secrets codés en dur."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from prorealtime_v2.config import EmailConfig

LOGGER = logging.getLogger(__name__)


class EmailSender:
    """Client SMTP optionnel."""

    def __init__(self, config: EmailConfig) -> None:
        self.config = config

    def send_text(self, subject: str, content: str) -> bool:
        """Envoie un email texte si la configuration SMTP est complète."""

        if not self.config.enabled:
            LOGGER.info("Email désactivé: configuration SMTP incomplète")
            return False

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.config.user
        message["To"] = self.config.recipient
        message.set_content(content)

        context = ssl.create_default_context()
        with smtplib.SMTP(self.config.host, self.config.port, timeout=30) as smtp:
            smtp.starttls(context=context)
            smtp.login(self.config.user, self.config.app_password)
            smtp.send_message(message)
        LOGGER.info("Email envoyé à %s", self.config.recipient)
        return True
