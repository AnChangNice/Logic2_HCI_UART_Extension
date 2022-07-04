# Logic2_HCI_UART_Extension
A HCI uart extension for Saleae Logic 2, and a script convert exported data to btsnoop file.

# Usage
1, Cauture HCI TX/RX data and decode them both with "Async Serial"

2, Use Logic2's "Load Existing Extesion" and open "Logic2_HCI_UART_Extension\HCI_UART\extension.json", then you will find "UART HCI" in your Analyzers.

3, Add two "UART HCI" analyzer and select right role for them "Host->Controller" or "Controller->Host" in "Role Choice"

4, Only keep the UART HCI's analyze data in data table

5, Export them both to CSV with "Use ISO8601 timestamps".

6, Run command "python csv2btsnoop.py hci.csv btsnoop.log" to get the btsnoop file.
