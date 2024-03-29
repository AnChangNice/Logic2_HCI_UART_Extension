# Logic2_HCI_UART_Extension
A HCI uart extension for Saleae Logic 2, and a script convert exported data to btsnoop file.

# Working flow
UART_HCI foler include a Logic2 extension analyzer could findout HCI packets from uart stream, but the analyzer don't know the data direction, so the user need select the correct role for them. The analyzer result will shown in data table's data colume, and only the UART HCI's result should be keeped. Then you could export to a CSV file with ISO timestamp. Last, run csv2btsnoop.py script to convert the csv to btsnoop log file.

# Usage
## 1, Cauture HCI TX/RX data and decode them both with "Async Serial"
![image](doc/analyzer_serial.png)

## 2, Use Logic2's "Load Existing Extesion" and open "Logic2_HCI_UART_Extension\HCI_UART\extension.json", then you will find "UART HCI" in your Analyzers.
![image](doc/add_existing_extension.png)
![image](doc/select_local_extension_json.png)
![image](doc/added_extension.png)

## 3, Add two "UART HCI" analyzers and select right role for them "Host->Controller" or "Controller->Host" in "Role Choice"
![image](doc/add_UART_HCI_analyzer.png)
![image](doc/analyzer_config.png)

## 4, Only keep the UART HCI's analyze data in data table
![image](doc/ExportTable.png)

## 5, Export them both to CSV with "Use ISO8601 timestamps".
![image](doc/export.png)

## 6, Run command "python csv2btsnoop.py hci.csv btsnoop.log" to get the btsnoop file. Or just drop csv file to csv2btsnoop.bat to generate btsnoop file.
![image](doc/csv2btsnoop.png)

## Now you could review the btsnoop log in Wireshark or any other tools.
![image](doc/Wireshark.png)
