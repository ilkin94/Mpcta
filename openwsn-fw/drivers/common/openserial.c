/**
\brief Definition of the "custom openserial" driver.

\author Fabien Chraim <chraim@eecs.berkeley.edu>, March 2012.
\author Thomas Watteyne <thomas.watteyne@inria.fr>, August 2016.
*/

#include "opendefs.h"
#include "openserial.h"
#include "IEEE802154E.h"
#include "neighbors.h"
#include "sixtop.h"
#include "icmpv6echo.h"
#include "idmanager.h"
#include "openqueue.h"
#include "openbridge.h"
#include "leds.h"
#include "schedule.h"
#include "uart.h"
#include "opentimers.h"
#include "openhdlc.h"
#include "schedule.h"
#include "icmpv6rpl.h"
#include "icmpv6echo.h"
#include "sf0.h"
#include "stdint.h"


/**
 * {These values define the command types}
 */
enum control_commands
{
    SET_DAG_ROOT = 0,
    GET_NEIGHBORS_COUNT,
    ADD_SLOT,
    REMOVE_SLOT,
    DUMP_RADIO_PACKETS
};

enum data_commands 
{
    INJECT_UDP_PACKET = 0,
    INJECT_TCP_PACKET
};


/*
 * Local variables (Variables used within this file)
 */
typedef struct {
    uint8_t buffer[10];
    uint8_t length;
} uart_buffer;

typedef struct {
    uint8_t packet_type;
    uint8_t packet_length;
    uint8_t payload;
}serial_packets;


openserial_vars_t openserial_vars;

// uart_buffer rx_buffer = {{0},0};
// uart_buffer tx_buffer = {{0},0};
uint8_t bytes_tx_count = 0;

//Defining transmission buffer for the uart.
CIRCBUF_DEF(tx_buffer,SERIAL_OUTPUT_BUFFER_SIZE);

//Receiving buffer for the uart.
CIRCBUF_DEF(rx_buffer,SERIAL_INPUT_BUFFER_SIZE);


//Local function declarations
uint8_t circular_buffer_push(circBuf_t *,uint8_t );

uint8_t circular_buffer_pop(circBuf_t *,uint8_t *);

uint8_t openserial_handleCommands(void);

uint8_t handle_control_commands(void);

uint8_t handle_data_commands(void);


//=========================== public ==========================================

//===== admin

void openserial_init() {
    // set callbacks
    uart_setCallbacks(
        isr_openserial_tx,
        isr_openserial_rx
    );
}

//===== scheduling

/**
 * @brief      {This function, for every 8 slots(function called after every 8 slots)
 *              reads contents of the received buffer then takes action according to 
 *              the received command}
 */
void openserial_startInput() {
    uint8_t idx_count,packet_len;

    INTERRUPT_DECLARATION();
    uart_clearTxInterrupts();
    uart_clearRxInterrupts();      // clear possible pending interrupts
    uart_enableInterrupts();       // Enable USCI_A1 TX & RX interrupt
    DISABLE_INTERRUPTS();

    //Here check whether buffer size is filled enough.
    //TODO: check the buffer fill level without accessing buffer members directly.
    if(rx_buffer.buffer[rx_buffer.tail] > rx_buffer.fill_level) {
        // openserial_printf("buffer isn't full enough\r\n",sizeof("buffer isn't full enough\r\n"));
        return;
    }

    if(circular_buffer_pop(&rx_buffer,&openserial_vars.reqFrame))
    {
        //openserial_printf("Popping a packet",sizeof("Popping a packet"));
        openserial_printf(openserial_vars.reqFrame,1);
        //first byte represents the length of the command, parse first byte, number of bytes.
        for(idx_count = 1; idx_count < openserial_vars.reqFrame[0];idx_count++)
            circular_buffer_pop(&rx_buffer,openserial_vars.reqFrame+idx_count);

        //Dump the read values for debugging purposes
        openserial_printf(openserial_vars.reqFrame,openserial_vars.reqFrame[0]);
        openserial_handleCommands();
    }
}

void openserial_startOutput() {
    uint8_t data = NULL;

    INTERRUPT_DECLARATION();
    //=== flush TX buffer,
    uart_clearTxInterrupts();
    uart_clearRxInterrupts();          // clear possible pending interrupts
    uart_enableInterrupts();           // Enable USCI_A1 TX & RX interrupt

    DISABLE_INTERRUPTS();

    if(circular_buffer_pop(&tx_buffer,&data))
        uart_writeByte(data);

    ENABLE_INTERRUPTS();
}

void openserial_stop() {

    /**
     * This function was originally used by openwsn for 
     * the purpose of processing the received commands
     * presently kept as stub. does nothing. 
     */
}

/**
 * @brief      {This function is added for logging purpose, prints the message to the serial port}
 *
 * @param      data_ptr  The data pointer
 * @param[in]  data_len  The data length
 *
 * @return     { description_of_the_return_value }
 */
uint8_t openserial_printf(char *data_ptr , uint8_t data_len) {
    uint8_t idx;
    INTERRUPT_DECLARATION();

    DISABLE_INTERRUPTS();
    //Here i am going to fill the tx_buffer which will be eventually printed to serial terminal.
    for(idx = 0 ;idx < data_len; idx++) 
    {
        if(!circular_buffer_push(&tx_buffer,data_ptr[idx]))
            break; // Signifies that ring buffer is full, break the loop
    }

    ENABLE_INTERRUPTS();
    return idx-1; // returning number of bytes printed.
}

uint8_t openserial_handleCommands(void) {
    if(openserial_vars.reqFrame[1] == 'C')
        handle_control_commands();
    else if(openserial_vars.reqFrame[1] == 'D')
        handle_data_commands();
    else
        openserial_printf("invalid serial command",sizeof("invalid serial command"));
}

uint8_t handle_control_commands() {
    uint8_t nbr_count;
    switch(openserial_vars.reqFrame[2]) {
        case 0:             //0 corresponds to set dagroot command.
            idmanager_setIsDAGroot(TRUE);
            break;
        case 1:             //1 corresponds to get neighbors count
            nbr_count = neighbors_getNumNeighbors();
            openserial_printf(&nbr_count,1);
            break;
        default:
            openserial_printf("unidentifiable control command\r\n",sizeof("Unidefiable control command\r\n"));
    }
}

uint8_t handle_data_commands() {
    switch(openserial_vars.reqFrame[2]) {
        case 0:         //0 corresponds to UDP packet so inject udp packet
        
    }

}


uint8_t inject_udp_packet()
{
    // don't run if not synch
   if (ieee154e_isSynch() == FALSE) return;
}

//=========================== interrupt handlers ==============================

/**
 * { this function gets called once the tx of byte is completed, Executed in isr
 *  useful for writing the next byte of data to the tx buffer
 *  executed in ISR, called from scheduler.c}
 */
void isr_openserial_tx() {
    // if(bytes_tx_count < rx_buffer.length) {
    //     uart_writeByte(rx_buffer.buffer[bytes_tx_count++]);
    // } else {
        // bytes_tx_count = 0;
        // rx_buffer.length = 0;
    // }
    uint8_t data = NULL;
    if(circular_buffer_pop(&tx_buffer,&data))
        uart_writeByte(data);
}

/**
 * { this function gets called when uart has received a byte, Executed in isr context
 *  useful for reading data from rxbuf
 *  executed in ISR, called from scheduler.c}
 */
void isr_openserial_rx() {
    // uint8_t cmd;
    // cmd = uart_readByte();
    // if(cmd == 0x01)
    //     idmanager_setIsDAGroot(TRUE);   //Here I will set the node as dagroot
    // rx_buffer.buffer[rx_buffer.length] = cmd;
    // //uart_writeByte(rx_buffer.buffer[rx_buffer.length]);
    // rx_buffer.length++;

    // if(rx_buffer.length >= 10) 
    // {
    //     uart_writeByte(neighbors_getNumNeighbors());
    //     // tx_buffer.length = rx_buffer.length-1;
    //     // rx_buffer.length = 0;
    // }
    // Here starts a critical section. Critical section is not needed for isr
    // hence commenting
    //INTERRUPT_DECLARATION();
    uint8_t data = uart_readByte();
    circular_buffer_push(&rx_buffer,data);
    //uart_writeByte(rx_buffer.head - rx_buffer.tail);

    //DISABLE_INTERRUPTS();

    //ENABLE_INTERRUPTS();
}

uint8_t circular_buffer_push(circBuf_t *buffer_ptr,uint8_t dataValue)
{
    uint8_t next = buffer_ptr->head + 1;

    if(next >= buffer_ptr->maxLen)
        next = 0;
    //This signifies that ring buffer is full, Hence blink error led and log the error
    if(next == buffer_ptr->tail)
    {
        leds_error_toggle();
        return FALSE;
        //TODO: Print the serial msg
    }
    buffer_ptr->buffer[buffer_ptr->head] = dataValue;
    buffer_ptr->head = next;
    buffer_ptr->fill_level++;
    return TRUE;
}

uint8_t circular_buffer_pop(circBuf_t *buffer_ptr,uint8_t *data)
{
    // if the head isn't ahead of the tail, we don't have any characters
    if (buffer_ptr->head == buffer_ptr->tail) {     // check if circular buffer is empty.
        data = NULL;
        return FALSE;           // and return with an error.
    }

    uint8_t next = buffer_ptr->tail + 1;
    if(next >= buffer_ptr->maxLen)
        next = 0;

    *data = buffer_ptr->buffer[buffer_ptr->tail]; // Read data and then move
    buffer_ptr->tail = next;
    buffer_ptr->fill_level--;
    return TRUE;
}




//Unused prototypes of functions.
//=========================== prototypes ======================================

// printing
owerror_t openserial_printInfoErrorCritical(
    char             severity,
    uint8_t          calling_component,
    uint8_t          error_code,
    errorparameter_t arg1,
    errorparameter_t arg2
);

// command handlers
void openserial_handleEcho(uint8_t* but, uint8_t bufLen);
void openserial_get6pInfo(uint8_t commandId, uint8_t* code,uint8_t* cellOptions,uint8_t* numCells,cellInfo_ht* celllist_add,cellInfo_ht* celllist_delete,uint8_t* listOffset,uint8_t* maxListLen,uint8_t ptr, uint8_t commandLen);

// misc
void openserial_board_reset_cb(opentimers_id_t id);

// HDLC output
void outputHdlcOpen(void);
void outputHdlcWrite(uint8_t b);
void outputHdlcClose(void);

// HDLC input
void inputHdlcOpen(void);
void inputHdlcWrite(uint8_t b);
void inputHdlcClose(void);

// sniffer
void sniffer_setListeningChannel(uint8_t channel);


/***************************************************************************************/
/* 
 * 
 * 
 * Only stubs, here onwards
 * 
 * 
 */
/**************************************************************************************/

void openserial_register(openserial_rsvpt* rsvp) {
    //stub
}

//===== printing

owerror_t openserial_printStatus(
    uint8_t             statusElement,
    uint8_t*            buffer,
    uint8_t             length
) {
    //Disabled
    return E_SUCCESS;
}

owerror_t openserial_printInfo(
    uint8_t             calling_component,
    uint8_t             error_code,
    errorparameter_t    arg1,
    errorparameter_t    arg2
) {
    //Disabled
    return E_SUCCESS;
}

owerror_t openserial_printError(
    uint8_t             calling_component,
    uint8_t             error_code,
    errorparameter_t    arg1,
    errorparameter_t    arg2
) {
    //Disabled
    return E_SUCCESS;
}

owerror_t openserial_printCritical(
    uint8_t             calling_component,
    uint8_t             error_code,
    errorparameter_t    arg1,
    errorparameter_t    arg2
) {
    //Disabled
    return E_SUCCESS;
}

owerror_t openserial_printData(uint8_t* buffer, uint8_t length) {
    //Disabled
    return E_SUCCESS;
}

owerror_t openserial_printSniffedPacket(uint8_t* buffer, uint8_t length, uint8_t channel) {
    //Disabled
    return E_SUCCESS;
}

//===== retrieving inputBuffer

uint8_t openserial_getInputBufferFilllevel() {
    //Disabled
    return E_SUCCESS;
}

uint8_t openserial_getInputBuffer(uint8_t* bufferToWrite, uint8_t maxNumBytes) {
    //Disabled
    return E_SUCCESS;
}

//===== debugprint

/**
\brief Trigger this module to print status information, over serial.

debugPrint_* functions are used by the openserial module to continuously print
status information about several modules in the OpenWSN stack.

\returns TRUE if this function printed something, FALSE otherwise.
*/
bool debugPrint_outBufferIndexes() {

    return TRUE;
}

//=========================== private =========================================

//===== printing

owerror_t openserial_printInfoErrorCritical(
    char             severity,
    uint8_t          calling_component,
    uint8_t          error_code,
    errorparameter_t arg1,
    errorparameter_t arg2
) {
    return E_SUCCESS;
}

//===== command handlers

void openserial_handleEcho(uint8_t* buf, uint8_t bufLen){
    // echo back what you received
    openserial_printData(
        buf,
        bufLen
    );
}

void openserial_get6pInfo(uint8_t commandId, uint8_t* code,uint8_t* cellOptions,uint8_t* numCells,cellInfo_ht* celllist_add,cellInfo_ht* celllist_delete,uint8_t* listOffset,uint8_t* maxListLen,uint8_t ptr, uint8_t commandLen){
    //Stubs function;
}

//===== misc

void openserial_board_reset_cb(opentimers_id_t id) {
    board_reset();
}

//===== hdlc (output)

/**
\brief Start an HDLC frame in the output buffer.
*/
port_INLINE void outputHdlcOpen() {

}
/**
\brief Add a byte to the outgoing HDLC frame being built.
*/
port_INLINE void outputHdlcWrite(uint8_t b) {

}
/**
\brief Finalize the outgoing HDLC frame.
*/
port_INLINE void outputHdlcClose() {

}

//===== hdlc (input)

/**
\brief Start an HDLC frame in the input buffer.
*/
port_INLINE void inputHdlcOpen() {

}
/**
\brief Add a byte to the incoming HDLC frame.
*/
port_INLINE void inputHdlcWrite(uint8_t b) {

}
/**
\brief Finalize the incoming HDLC frame.
*/
port_INLINE void inputHdlcClose() {

}