import csv
import sys
from datetime import datetime
import struct

help = """
usage: python [csv input] [btsnoop output]
"""

class BTSNOOP():
    
    def __init__(self):
        self.packet_records = []

    def __pack(self, size, val):
        pass

    def save_packet(self, time_stamp_us, direction_h_c, data_array):

        # Original Length
        Original_Length = 4 + len(data_array) + 4 + 4 + 8

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
    

if __name__ == "__main__":
    # get args
    args = sys.argv[1:]

    if len(args) == 1 and (args[0] == 'help' or args[0] == '-h'):
        print(help)
        sys.exit()

    if len(args) != 2:
        print("Invalid args!")
        print(help)
        sys.exit()

    input_csv_path = args[0]
    output_btsnoop_path = args[1]

    input_csv = open(input_csv_path, 'r')

    csv = csv.DictReader(input_csv)

    btsnoop = BTSNOOP()

    for row in csv:
        # time stamp
        time_stemp_us = get_time_stamp(row['start_time'])

        # data directions
        direction_h_c = row['data'][:4]
        if row['data'][:4] == "H->C":
            pass
        elif row['data'][:4] == "C->H":
            pass
        else:
            raise "Data not 'H->C' or 'C->H'!"
            sys.exit()
        
        # data
        data_str = row['data'][5:].split(' ')
        data_array = [int(x, 16) for x in data_str]

        btsnoop.save_packet(time_stemp_us, direction_h_c, data_array)

    btsnoop.save_to_file(output_btsnoop_path)



