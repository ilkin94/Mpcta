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
    GET_NODE_TYPE,          //This is to check whether the node is dagroot or not, This will be useful for python code.
    GET_NEIGHBORS_COUNT,
    GET_NEIGHBORS,
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

uint8_t start_frame_flag = 0x7e;

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

uint8_t inject_udp_packet(void);

uint8_t send_response_packet(uint8_t *,uint8_t);



uint8_t ping_packet[] = {0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x02,0xF1,0x7A,0x55,0x3A, \
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x02,0x80, \
    0x00,0x28,0x74,0x18,0xBC,0x0C,0x0E,0x00,'Y','A','D','H','U','N','A','N','D'};

static const uint8_t packet_dst_addr[]   = {
   0xbb, 0xbb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
   0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01
};
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


    //leds_error_toggle();
    //HERE I NEED TO CLEAR UP THE BUFFER, IF 0X7E IS NOT FOUND IN THE BEGINNING OF THE BUFFER, THEN CHECK FOR BUFFER FILL LEVEL
    //THIS IS DONE TO MAKE SURE THAT, IF WE LOOSE THE BEGINNING OF THE FRAME DUE TO SCHEDULING, WE HAVE TO THROW AWAY THE PARTIAL FRAME
    //SITTING IN THE RX BUFFER BECAUSE THIS IS A MALFORMED FRAME.
    //START PARSING THE FRESH FRAME SO IT SHOULD CONTAIN 0X7E AS THE FIRST BYTE.
    do
    {
        //openserial_printf(&rx_buffer.fill_level,1);
        if(!circular_buffer_pop(&rx_buffer,&openserial_vars.reqFrame)) 
        {
            ENABLE_INTERRUPTS();
            return;
        }
        //openserial_printf("ffff",sizeof("ffff")-1);
    }while(start_frame_flag != openserial_vars.reqFrame[0] && rx_buffer.fill_level);

    //Here check whether buffer size is filled enough.
    //TODO: check the buffer fill level without accessing buffer members directly.
    if(rx_buffer.buffer[rx_buffer.tail] > rx_buffer.fill_level) 
    {
        //openserial_printf("buffer isn't full enough\r\n",sizeof("buffer isn't full enough\r\n"));
        //leds_error_toggle();
        return;
    }

    if(circular_buffer_pop(&rx_buffer,&openserial_vars.reqFrame))
    {
        //openserial_printf(openserial_vars.reqFrame,1,'D');
        //first byte represents the length of the command, parse first byte, number of bytes.
        for(idx_count = 1; idx_count < openserial_vars.reqFrame[0];idx_count++)
            circular_buffer_pop(&rx_buffer,openserial_vars.reqFrame+idx_count);

        //Dump the read values for debugging purposes
        //openserial_printf(openserial_vars.reqFrame,openserial_vars.reqFrame[0],'D');
        openserial_handleCommands();
        //leds_error_off();
    }
    ENABLE_INTERRUPTS();
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
uint8_t openserial_printf(char *data_ptr , uint8_t data_len,uint8_t type) {
    uint8_t idx;
    INTERRUPT_DECLARATION();

    DISABLE_INTERRUPTS();

    if(!circular_buffer_push(&tx_buffer,start_frame_flag))
        leds_error_on();

    if(!circular_buffer_push(&tx_buffer,data_len+2)) //+2 because we include type of message byte and length byte as part of the packet
        leds_error_on();

    if(!circular_buffer_push(&tx_buffer,type)) //+1 because we include type of message byte as part of the packet
        leds_error_on();

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
}

uint8_t handle_control_commands() {
    uint8_t nbr_count,index,nbr_list[40],node_type = FALSE;
    neighborRow_t* neighbor;
    switch(openserial_vars.reqFrame[2]) 
    {
        case SET_DAG_ROOT:             //0 corresponds to set dagroot command.
            idmanager_setIsDAGroot(TRUE);
            break;
        case GET_NODE_TYPE:             //1 corresponds to get node type 1 means dagroot, zero means normal mote
            node_type = idmanager_getIsDAGroot();
            send_response_packet(&node_type,1);
            break;
        case GET_NEIGHBORS_COUNT:
            nbr_count = neighbors_getNumNeighbors();
            send_response_packet(&nbr_count,1);
            break;
        case GET_NEIGHBORS:
            nbr_count = neighbors_getNumNeighbors();
            for(index = 0;index < nbr_count;index++)
            {
                if (neighbors_getInfo(index, &neighbor) != FALSE)
                    memcpy(nbr_list+index*8,&neighbor->addr_64b.addr_64b,8);
            }
            send_response_packet(nbr_list,nbr_count*8);
            break;
    }
}

uint8_t handle_data_commands() {
    switch(openserial_vars.reqFrame[2]) {
        case 0:         //0 corresponds to UDP packet so inject udp packet
        inject_udp_packet();
        //leds_error_toggle();
        break;
        default:
            ;
    }
}

uint8_t send_response_packet(uint8_t *data,uint8_t length)
{
    uint8_t resp[50] = {0};
    //In this first byte takes into account length byte, command category, command sub category,length of result
    resp[0] = openserial_vars.reqFrame[1];
    resp[1] = openserial_vars.reqFrame[2];
    memcpy(resp+2,data,length);
    openserial_printf(resp,length+2,'R'); //resp[0] contains the length of the packet
}


uint8_t inject_udp_packet()
{
    OpenQueueEntry_t*    pkt;
    // don't run if not synch
    if (ieee154e_isSynch() == FALSE) return;

    //This is because, since only mac layer is running in DAGroot udp_send always fails so
    //just return from here.
    if (idmanager_getIsDAGroot()) {
        //Here I have to call openbridge to inject packet and packet has to be in iphc format.
        openbridge_triggerData();
          return;
    }
    //Now start forming the udp packet.
    // get a free packet buffer.
    pkt = openqueue_getFreePacketBuffer(COMPONENT_OPENSERIAL);
    if (pkt == NULL) {
        leds_error_toggle();
        return;
    }
    pkt->owner                         = COMPONENT_OPENSERIAL;
    pkt->creator                       = COMPONENT_OPENSERIAL;
    pkt->l4_protocol                   = IANA_UDP;
    pkt->l4_destination_port           = WKP_UDP_OPENSERIAL;
    pkt->l4_sourcePortORicmpv6Type     = WKP_UDP_OPENSERIAL;
    pkt->l3_destinationAdd.type        = ADDR_128B;
    memcpy(&pkt->l3_destinationAdd.addr_128b[0],packet_dst_addr,16);

    packetfunctions_reserveHeaderSize(pkt,openserial_vars.reqFrame[0]-3);
    memcpy(&pkt->payload[0],openserial_vars.reqFrame+3,openserial_vars.reqFrame[0]-3);

    if ((openudp_send(pkt))==E_FAIL) {
        openqueue_freePacketBuffer(pkt);
        leds_error_toggle();
    }
}


//===== retrieving inputBuffer for openbridge packet inject

uint8_t openserial_getInputBufferFilllevel()
{
    return openserial_vars.reqFrame[0]-3;
}

uint8_t openserial_getInputBuffer(uint8_t* bufferToWrite, uint8_t maxNumBytes)
{
    //openserial_printf(openserial_vars.reqFrame+3,openserial_vars.reqFrame[0]-3,'D');
    memcpy(bufferToWrite,openserial_vars.reqFrame+3,openserial_vars.reqFrame[0]-3);
    return openserial_vars.reqFrame[0]-3;
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