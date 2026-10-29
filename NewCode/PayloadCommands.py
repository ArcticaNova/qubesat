import board
import time
import pycubed
import digitalio
import busio

class PayloadCommands() :
    uart = busio.UART(board.TX2, board.RX2, baudrate = 9600)
    temperature = [0, 0, 0, 0, 0, 0, 0]

    def sendTemperatureCheck(self) :

        receivingMessage = ""
        self.temperature = #whatever the temperature is right now
        sendingMessage = "T\n" #arbitrary 25C value
        print("Sending data...")
        self.uart.write(sendingMessage)

            #for every T that I transmit, Chandrark will receive that
            #everytime chandrark receives the T, he will transmit the temperature of the 7 sensors that i will receive
            #will need to update the temperature array everytime this happens and convert that number into celsius

            #implement a while loop for that if the last character isnt the sentinel character, then keep reading temperature messages updated from chandrarks transmissions
            #for now sentinel character can be "\n"
        while (receivingMessage[-1] != "\n") : ##sentinelCharacter will be whatever string Chandrark sends which is exampleString[-1]

        receivingMessage = receivingMessage[:-1] #gonna happen after the while loop finishes
        self.temperature = #comma split of whatever chandrark sends me

    