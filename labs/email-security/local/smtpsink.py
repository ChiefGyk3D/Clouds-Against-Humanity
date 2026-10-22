#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""smtpsink.py OUTFILE [PORT]: a tiny SMTP receiver on 127.0.0.1 that prints the conversation.

It accepts one message, writes it to OUTFILE, and exits. It listens on the loopback address only,
caps a message at 100 KB and a connection at 15 seconds, and speaks just enough SMTP (RFC 5321)
to show that the ENVELOPE (MAIL FROM, RCPT TO) is separate from the HEADERS (From, To) in the message.
It does no relaying and delivers nothing.
"""
import asyncio
import sys

MAX_BYTES = 100_000


async def handle(reader, writer, outfile, done):
    def say(line):
        print("S:", line)
        writer.write((line + "\r\n").encode())

    try:
        say("220 sink.test ESMTP lab sink")
        data_mode, body = False, []
        while True:
            raw = await asyncio.wait_for(reader.readline(), timeout=15)
            if not raw:
                break
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if data_mode:
                if line == ".":
                    data_mode = False
                    with open(outfile, "w", newline="") as f:
                        f.write("\r\n".join(l[1:] if l.startswith("..") else l for l in body) + "\r\n")
                    say("250 2.0.0 queued (to a file, nowhere else)")
                elif sum(len(l) for l in body) > MAX_BYTES:
                    say("552 5.3.4 too big")
                    break
                else:
                    body.append(line)
                continue
            print("C:", line)
            cmd = line.upper()
            if cmd.startswith(("EHLO", "HELO")):
                say("250 sink.test")
            elif cmd.startswith(("MAIL FROM:", "RCPT TO:", "RSET", "NOOP")):
                say("250 2.1.0 ok")
            elif cmd == "DATA":
                data_mode = True
                say("354 end data with <CRLF>.<CRLF>")
            elif cmd == "QUIT":
                say("221 2.0.0 bye")
                break
            else:
                say("502 5.5.2 command not recognized")
            await writer.drain()
        await writer.drain()
    except (asyncio.TimeoutError, ConnectionError):
        pass
    finally:
        writer.close()
        done.set()


async def main(outfile, port):
    done = asyncio.Event()
    server = await asyncio.start_server(lambda r, w: handle(r, w, outfile, done), "127.0.0.1", port)
    print(f"listening on 127.0.0.1:{port}; waiting for one message", flush=True)
    async with server:
        await asyncio.wait_for(done.wait(), timeout=120)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: smtpsink.py OUTFILE [PORT]")
    asyncio.run(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2525))
