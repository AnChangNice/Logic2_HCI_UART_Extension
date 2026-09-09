
  # UART HCI

A Analyzer could find Bluetooth HCI UART packet from Async Serial result stream.

## Getting started

Add to your Logic2 Local Extension with Extesion -> Options -> Load Existing Extesion

## How it works

Each analyzer instance watches one UART wire. Instead of trusting a single byte to be a
packet start, it looks for an alignment where several consecutive packets all parse
cleanly (chain validation), so a capture that begins mid-packet, or a stretch of
wrong-baud-rate garbage, does not turn into bogus packets. When the stream goes bad
(illegal type, impossible length, or a UART framing error) it drops sync and hunts for
the next good alignment - which is what makes captures that span a board reset
(good frames / garbage / good frames) decode correctly.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| Role Choice | Host->Controller | Direction label used only until a Command/Event proves the real direction (Auto mode), or always (Manual mode). |
| Decode Mode | Always | `Always` decodes from the first good alignment. `Trigger` waits for a trigger packet first. |
| Decode Trigger Frame | | Packet(s) that start the output, e.g. `01 03 0C 00`. Use `\|` for alternatives and `??` for a wildcard byte: `01 03 0C 00 \| 04 0E 04 ?? 03 0C 00`. Matched against whole packets, so a sequence inside a payload never triggers. |
| Direction Mode | Auto | `Auto` labels each packet from its type (Command -> H->C, Event -> C->H), so swapped TX/RX probes are corrected automatically. `Manual` always uses Role Choice. |
| Sync Packets | 3 | Consecutive valid packets required to trust an alignment. Higher is stricter but leaves more packets un-decoded at the very end of a capture. |
| Trigger Re-arm | On Resync | `On Resync` re-requires the trigger after every loss of sync, so each session after a board reset filters its own pre-Reset traffic. `Once` triggers a single time. |
