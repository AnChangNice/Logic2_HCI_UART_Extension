import csv
import sys
from datetime import datetime
import struct
import os

help = """
usage: python [csv input] [btsnoop output]
"""

DIRECTION_H_C = "H->C"
DIRECTION_C_H = "C->H"

# H4 packet type -> the only direction that packet type can legally travel.
# ACL(0x02) / SCO(0x03) / ISO(0x05) flow both ways, so they cannot be used to tell
# whether the direction labels in the CSV are trustworthy.
ANCHOR_PACKET_DIRECTION = {
    0x01: DIRECTION_H_C,   # HCI Command
    0x04: DIRECTION_C_H,   # HCI Event
}

class BTSNOOP():

    def __init__(self):
        self.packet_records = []

    def __pack(self, size, val):
        pass

    def save_packet(self, time_stamp_us, direction_h_c, data_array):

        # Original Length
        Original_Length = len(data_array)

        # Included Length
        Included_Length = len(data_array)

        # Packet Flags
        Packet_Flags = 0
        if direction_h_c == "C->H":
            Packet_Flags = 1

        if data_array[0] == 0x01 or data_array[0] == 0x04:
            Packet_Flags |= 1<<1

        # Cumulative Drops
        Cumulative_Drops = 0

        # Timestamp Microseconds
        byte_s = struct.pack(">IIIIQ", Original_Length, Included_Length, Packet_Flags, Cumulative_Drops, time_stamp_us)
        packet_record = list(byte_s)

        # Packet Data
        packet_record += data_array

        self.packet_records.append(packet_record)

    def save_to_file(self, file_path):
        file = open(file_path, 'wb+')

        # write btsnoop header
        file.write(bytes([0x62,0x74,0x73,0x6E,0x6F,0x6F,0x70,0x00]))   #Identification Pattern
        file.write(bytes([0x00,0x00,0x00,0x01]))   #Version Number
        file.write(bytes([0x00,0x00,0x03,0xEA]))   #Datalink Type: 1002 - HCI UART (H4)

        # write all packet records
        for record in self.packet_records:
            file.write(bytes(record))

        # save
        file.close()

def get_time_stamp(iso_8601_str):
    # 2022-07-02T13:03:04.042449200+00:00
    time_str_a = iso_8601_str[:26]
    time_str_b = iso_8601_str[29:]

    time_str_s = time_str_a + time_str_b
    d = datetime.strptime(time_str_s, "%Y-%m-%dT%H:%M:%S.%f%z")

    time_stamp_us = int(d.timestamp() * 1000 * 1000) + 0x00dcddb30f2f8000 # add 1970 years with us unit.

    return time_stamp_us


def read_csv_rows(csv_path):
    """Read the CSV into memory. The input CSV is only ever opened read-only."""
    with open(csv_path, 'r', newline='') as input_csv:
        reader = csv.DictReader(input_csv)
        return reader.fieldnames, list(reader)


def parse_data_field(data_field):
    """Split a data cell like 'H->C:01 03 0C 00' into ('H->C', [0x01, 0x03, 0x0C, 0x00])."""
    direction_h_c = data_field[:4]
    if direction_h_c not in (DIRECTION_H_C, DIRECTION_C_H):
        raise ValueError(f"Data not '{DIRECTION_H_C}' or '{DIRECTION_C_H}': {data_field!r}")

    data_str = data_field[5:].split(' ')
    data_array = [int(x, 16) for x in data_str if x]

    return direction_h_c, data_array


def swap_data_field(data_field):
    """Flip the direction label of a data cell, leaving the payload text untouched."""
    direction_h_c = data_field[:4]
    swapped = DIRECTION_C_H if direction_h_c == DIRECTION_H_C else DIRECTION_H_C

    return swapped + data_field[4:]


def count_direction_mismatch(rows):
    """Check the CSV direction labels against the HCI packet types.

    HCI Command (0x01) can only be H->C and HCI Event (0x04) can only be C->H, so those
    packets are used as anchors. Returns (mismatch_count, anchor_count).
    """
    mismatch_count = 0
    anchor_count = 0

    for row in rows:
        direction_h_c, data_array = parse_data_field(row['data'])

        if len(data_array) == 0:
            continue

        expected_direction = ANCHOR_PACKET_DIRECTION.get(data_array[0])
        if expected_direction is None:
            continue   # ACL/SCO/ISO: direction cannot be derived from the packet type

        anchor_count += 1
        if direction_h_c != expected_direction:
            mismatch_count += 1

    return mismatch_count, anchor_count


def write_csv_rows(csv_path, fieldnames, rows):
    with open(csv_path, 'w', newline='') as output_csv:
        writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fix_swapped_direction(input_csv_path):
    """Detect and repair a capture recorded with the TX/RX probes swapped.

    A single Command/Event packet whose direction contradicts its packet type means the
    whole CSV was labelled the wrong way round, so every row gets its direction swapped
    - including the ACL/SCO/ISO frames that cannot be checked on their own.

    The input CSV is never modified. Returns the path of the '_fixed.csv' file when a
    repair was needed, otherwise the original path.
    """
    fieldnames, rows = read_csv_rows(input_csv_path)

    mismatch_count, anchor_count = count_direction_mismatch(rows)

    if anchor_count == 0:
        print("no HCI Command/Event packet found, direction check skipped.")
        return input_csv_path

    if mismatch_count == 0:
        print(f"direction check passed ({anchor_count} command/event packets).")
        return input_csv_path

    for row in rows:
        row['data'] = swap_data_field(row['data'])

    root, ext = os.path.splitext(input_csv_path)
    fixed_csv_path = root + '_fixed' + ext

    write_csv_rows(fixed_csv_path, fieldnames, rows)

    print(f"TX/RX swapped: {mismatch_count} of {anchor_count} command/event packets "
          f"contradict their packet type.")
    print(f"all {len(rows)} rows swapped into {fixed_csv_path}")

    return fixed_csv_path


if __name__ == "__main__":
    # get args
    args = sys.argv[1:]

    if len(args) == 1:
        input_csv_path = args[0]
        output_btsnoop_path = input_csv_path[:-4] + '.log'
    elif len(args) == 2:
        input_csv_path = args[0]
        output_btsnoop_path = args[1]
    else:
        print(help)
        sys.exit()

    if not os.path.exists(input_csv_path):
        print("input path not exist!")
        sys.exit()

    if os.path.exists(output_btsnoop_path):
        print("input path already exist!")
        sys.exit()

    # Check the TX/RX direction labels, and build the btsnoop log from the repaired CSV
    # when the capture turns out to be reversed. This is a safety net for older captures
    # and for the Manual direction mode; the analyzer's Auto mode normally fixes the
    # direction before it ever reaches the CSV.
    source_csv_path = fix_swapped_direction(input_csv_path)

    _, rows = read_csv_rows(source_csv_path)

    btsnoop = BTSNOOP()

    for row in rows:
        # time stamp
        time_stemp_us = get_time_stamp(row['start_time'])

        # data directions and data
        direction_h_c, data_array = parse_data_field(row['data'])

        btsnoop.save_packet(time_stemp_us, direction_h_c, data_array)

    btsnoop.save_to_file(output_btsnoop_path)
