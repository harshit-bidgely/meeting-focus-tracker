"""SMTP email client for sending meeting summary reports.

Supports plain SMTP, STARTTLS, and SSL/TLS connections.
All credential values come from Config and are never hardcoded here.
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class EmailClient:
    """Send HTML + plain-text emails via SMTP.

    Constructor args mirror the Config fields so this class can be
    instantiated directly from Config values without extra coupling.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        sender_email: str,
        use_tls: bool = True,
        use_ssl: bool = False,
        timeout: int = 30,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.sender_email = sender_email
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout

    def send(
        self,
        to_emails: list[str],
        subject: str,
        html_body: str,
        text_body: str = "",
    ) -> bool:
        """Send a multipart email to *to_emails*.

        Attaches the plain-text part first (lowest preference) and the
        HTML part second so mail clients that support HTML display that.

        Returns:
            True  — email accepted by the SMTP server.
            False — sending failed (details logged at ERROR level).
        """
        if not to_emails:
            logger.warning("EmailClient.send() called with empty recipient list — skipping")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(to_emails)

        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if self.use_ssl:
                with smtplib.SMTP_SSL(
                    self.smtp_host, self.smtp_port, timeout=self.timeout
                ) as server:
                    self._authenticate(server)
                    server.sendmail(self.sender_email, to_emails, msg.as_string())
            else:
                with smtplib.SMTP(
                    self.smtp_host, self.smtp_port, timeout=self.timeout
                ) as server:
                    if self.use_tls:
                        server.starttls()
                    self._authenticate(server)
                    server.sendmail(self.sender_email, to_emails, msg.as_string())

            logger.info(
                "Meeting summary email sent to %d recipient(s): %s",
                len(to_emails),
                ", ".join(to_emails),
            )
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "SMTP authentication failed for user '%s' on %s:%s",
                self.smtp_user,
                self.smtp_host,
                self.smtp_port,
            )
        except smtplib.SMTPException as exc:
            logger.error("SMTP error while sending email: %s", exc)
        except OSError as exc:
            logger.error(
                "Network error connecting to %s:%s — %s",
                self.smtp_host,
                self.smtp_port,
                exc,
            )

        return False

    def _authenticate(self, server: smtplib.SMTP) -> None:
        """Login only when credentials are provided."""
        if self.smtp_user and self.smtp_password:
            server.login(self.smtp_user, self.smtp_password)
