*&---------------------------------------------------------------------*
*& Include          ZDCDF001TOP
*&---------------------------------------------------------------------*

* 004(ADD)↓------------------------------------------------
*-----------------------------------------------------------------------
* Type definition
*-----------------------------------------------------------------------
TYPES:
  BEGIN OF TA_DD03L,
    FIELDNAME TYPE DD03L-FIELDNAME,
    ROLLNAME  TYPE DD03L-ROLLNAME,
  END   OF TA_DD03L.
TYPES: TAT_DD03L TYPE STANDARD TABLE OF TA_DD03L.
* 004(ADD)↑------------------------------------------------

*-----------------------------------------------------------------------
* Variable definition
*-----------------------------------------------------------------------
DATA:
  WK_IFID         TYPE ZDCDIFT01-IFID     ##NEEDED,                           " Interface ID
  WK_SYSID        TYPE ZDCDIFT02-SYSID    ##NEEDED,                           " System ID
* 012(ADD)↓------------------------------------------------
  FLG_COMMIT_SYNC TYPE FLAG.                                            " Synchronized Commit Flag
* 012(ADD)↑------------------------------------------------
*-----------------------------------------------------------------------
* Work Area definition
*-----------------------------------------------------------------------
DATA:
  WA_IFHEAD TYPE ZDCDIFT03          ##NEEDED,                           " Interface Definition header
  WA_EXINFO TYPE ZDCD_EXINFO_S01    ##NEEDED.                           " Common Execution Information
*-----------------------------------------------------------------------
* Internal table definition
*-----------------------------------------------------------------------
DATA:
  IT_COMM   TYPE SLIS_T_LISTHEADER  ##NEEDED.                           " Header table for top of page
*-----------------------------------------------------------------------
* CONSTANTS DECLARATION
*-----------------------------------------------------------------------
CONSTANTS:
  BEGIN OF C_MSGTYPE,
    SUCCESS TYPE SYST_MSGTY VALUE 'S',                                  " Success Message
    ERROR   TYPE SYST_MSGTY VALUE 'E',                                  " Error Message
    INFO    TYPE SYST_MSGTY VALUE 'I',                                  " Information Message
    WARNING TYPE SYST_MSGTY VALUE 'W',                                  " Warning Message
    ABEND   TYPE SYST_MSGTY VALUE 'A',                                  " Abend Message
  END OF C_MSGTYPE,
  BEGIN OF C_SENDMODE,
    TAB_OP_NO_UPD_IF_FLG TYPE ZDCDESENDMODE VALUE '1',                   " No update of Table output-Linked flag
    TAB_FILE_OP          TYPE ZDCDESENDMODE VALUE '2',                   " Table output and file output
    FILE_OP              TYPE ZDCDESENDMODE VALUE '3',                   " Data conversion only file output
    TAB_OP_UPD_IF_FLG    TYPE ZDCDESENDMODE VALUE '4',                   " Update data output-Linked flag
  END OF C_SENDMODE,
  C_CONTEXT_S01  TYPE BALTABNAME VALUE 'ZDCD_CONTEXT_S01',            " Context Structure
  C_LISTHEAD_TYP TYPE C VALUE 'S',                                    " List header type
  C_ALV_S01      TYPE DD02L-TABNAME VALUE 'ZDCD_ALV_S01',             " ALV structure for transmission
  BEGIN OF C_FIELDNAME,
    KEYVAL1  TYPE SLIS_FIELDNAME VALUE 'KEYVAL1',                       " Key value 1
    KEYVAL2  TYPE SLIS_FIELDNAME VALUE 'KEYVAL2',                       " Key value 2
    KEYVAL3  TYPE SLIS_FIELDNAME VALUE 'KEYVAL3',                       " Key value 3
    KEYVAL4  TYPE SLIS_FIELDNAME VALUE 'KEYVAL4',                       " Key value 4
    KEYVAL5  TYPE SLIS_FIELDNAME VALUE 'KEYVAL5',                       " Key value 5
    KEYVAL6  TYPE SLIS_FIELDNAME VALUE 'KEYVAL6',                       " Key value 6
    KEYVAL7  TYPE SLIS_FIELDNAME VALUE 'KEYVAL7',                       " Key value 7
    KEYVAL8  TYPE SLIS_FIELDNAME VALUE 'KEYVAL8',                       " Key value 8
    KEYVAL9  TYPE SLIS_FIELDNAME VALUE 'KEYVAL9',                       " Key value 9
    KEYVAL10 TYPE SLIS_FIELDNAME VALUE 'KEYVAL10',                      " Key value 10
* 004(ADD)↓------------------------------------------------
    MSGV1    TYPE SLIS_FIELDNAME VALUE 'MSGV1',                         "メッセージ変数 01
    MSGV2    TYPE SLIS_FIELDNAME VALUE 'MSGV2',                         "メッセージ変数 02
    MSGV3    TYPE SLIS_FIELDNAME VALUE 'MSGV3',                         "メッセージ変数 03
    MSGV4    TYPE SLIS_FIELDNAME VALUE 'MSGV4',                         "メッセージ変数 04
* 004(ADD)↑------------------------------------------------
  END OF C_FIELDNAME,
  C_FLD_INDEX TYPE I VALUE 60,                                          " Field index
  C_SEL_TYPE  TYPE RSSCR_KIND VALUE 'P',                                 " Selection screen element type
  C_ACT_STAT  TYPE AS4LOCAL VALUE 'A',                                   " Activation State of Repository Object
  C_SEP_COLON TYPE C VALUE ':',                                         " Separator ":"
  BEGIN OF C_SEL_FIELD,
    P_IFID   TYPE RSSCR_NAME VALUE 'P_IFID',                           " Interface ID
    P_SYSID  TYPE RSSCR_NAME VALUE 'P_SYSID',                          " System ID
    CB_FOUT  TYPE RSSCR_NAME VALUE 'CB_FOUT',                          " File Output Dest. Change
    P_LOGFNM TYPE RSSCR_NAME VALUE 'P_LOGFNM',                         " Logical File Name
    P_FPATH  TYPE RSSCR_NAME VALUE 'P_FPATH',                          " Output File Path
    P_FNAME  TYPE RSSCR_NAME VALUE 'P_FNAME',                          " Output File Name
  END OF C_SEL_FIELD,
  BEGIN OF C_ROLLNAME,
    IFID        TYPE ROLLNAME VALUE 'ZDCDEIFID',                        " Interface ID
    SYSID       TYPE ROLLNAME VALUE 'ZDCDESYSID',                       " System ID
    FOP_DESTCHG TYPE ROLLNAME VALUE 'ZDCDELBLFOUT',                     " File Output Dest. Change
    LOG_FNAME   TYPE ROLLNAME VALUE 'ZDCDELOGFNAME',                    " Logical File Name
    OP_FPATHN   TYPE ROLLNAME VALUE 'ZDCDEFILEPATH',                    " Output File Path
    OP_FNAME    TYPE ROLLNAME VALUE 'ZDCDEFILENAME',                    " Output File Name
    FRM_TXT     TYPE ROLLNAME VALUE 'ZDCDEBL_FRM',                      " Frame Text
    GUID        TYPE ROLLNAME VALUE 'ZDCDEGUID',                        " GUID
    OP_FPATH    TYPE ROLLNAME VALUE 'ZDCDELBLPATH',                     " Output file path
    NO_ITM_PROC TYPE ROLLNAME VALUE 'ZDCDECNTSUB',                      " No. of items to be processed
    NO_SUCC     TYPE ROLLNAME VALUE 'ZDCDECNTSCC',                      " No. of successess
    NO_FAIL     TYPE ROLLNAME VALUE 'ZDCDECNTERR',                      " No. of failures
  END OF C_ROLLNAME,

  C_PROGRAM_ID    TYPE PROGRAM_ID VALUE 'Z_DCD_REQUEST_OUTPUT',         " Program ID
  C_PARAM_ID      TYPE ZDCDECMPID VALUE 'APPLICATION_LOG',              " Parameter ID
  C_REG_OBJECT    TYPE BALOBJ_D   VALUE 'ZDCDIF002',                    " Regulated object
  C_REG_SUBOBJECT TYPE BALSUBOBJ  VALUE 'GENERAL'.                      " Regulated sub-object



*----------------------------------------------------------------------*
*Selection-screen defintion
*----------------------------------------------------------------------*
SELECTION-SCREEN BEGIN OF BLOCK BL_COM1 WITH FRAME.
  PARAMETERS : P_IFID  TYPE ZDCDEIFID OBLIGATORY,                       " Interface ID
               P_SYSID TYPE ZDCDESYSID OBLIGATORY.                      " System ID

  SELECTION-SCREEN BEGIN OF BLOCK BL_COM2 WITH FRAME TITLE WA_TITLE.
    PARAMETERS : CB_FOUT      AS CHECKBOX,                              " File Destination Change
                 P_LOGFNM(60) TYPE C,                                   " Logical File Name
*013(MOD)↓--------------------------------------------------
*                 P_FPATH(255) TYPE C,                                   " Output File Path
                 P_FPATH      TYPE ZDCDEFILEPATH,                            " Output File Path
*013(MOD)↑--------------------------------------------------
*001(MOD)↓--------------------------------------------------
*                P_FNAME      TYPE STRING.                              " Output File Name
*003(MOD)↓--------------------------------------------------
*                P_FNAME      TYPE CHAR128.                             " Output File Name
                 P_FNAME      TYPE ZDCDEFILENAME.                       " Output File Name
*003(MOD)↑--------------------------------------------------
*001(MOD)↑--------------------------------------------------
  SELECTION-SCREEN END OF BLOCK BL_COM2.
SELECTION-SCREEN END OF BLOCK BL_COM1.
