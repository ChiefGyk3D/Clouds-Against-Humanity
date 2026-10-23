#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""smtpsend.py [PORT]: send one message to the lab sink with an ENVELOPE sender that differs from the From header.

Only ever connects to 127.0.0.1. The names are reserved example names.
"""
import smtplib
import sys
from email.message import EmailMessage

port = int(sys.argv[1]) if len(sys.argv) > 1 else 2525
m = EmailMessage()
m["From"] = '"CEO" <ceo@example.test>'  # what the reader sees
m["To"] = "bob@receiver.test"
m["Subject"] = "Envelope versus headers"
m.set_content("The envelope sender is not the From header.\n")
with smtplib.SMTP("127.0.0.1", port, timeout=10, local_hostname="client.lab.test") as s:
    s.set_debuglevel(0)
    s.sendmail("attacker@random-host.test", ["bob@receiver.test"], m.as_bytes())  # what the server is told
print("sent")
