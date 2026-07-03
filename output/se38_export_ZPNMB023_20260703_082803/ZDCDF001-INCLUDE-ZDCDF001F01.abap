*&---------------------------------------------------------------------*
*& Include          ZDCDF001F01
*&---------------------------------------------------------------------*
*&---------------------------------------------------------------------*
*&      Form FM_INPUT_CHECK
*&---------------------------------------------------------------------*
*&      Input check
*&---------------------------------------------------------------------*
FORM FM_INPUT_CHECK_BL_COM1.

* Interface ID Parameter Check
SELECT SINGLE IFID
  FROM ZDCDIFT01
  INTO WK_IFID
 WHERE IFID = P_IFID
   AND LOEVM <> ABAP_TRUE.
IF SY-SUBRC <> 0.
  MESSAGE S017(ZDCD001) WITH P_IFID DISPLAY LIKE C_MSGTYPE-ERROR.
  LEAVE SCREEN.
ENDIF.

* System ID Parameter Check
SELECT SINGLE SYSID
  FROM ZDCDIFT02
  INTO WK_SYSID
 WHERE SYSID = P_SYSID
   AND LOEVM <> ABAP_TRUE.
IF SY-SUBRC <> 0.
  MESSAGE S018(ZDCD001) WITH P_SYSID DISPLAY LIKE C_MSGTYPE-ERROR.
  LEAVE SCREEN.
ENDIF.

* Common execution information setting
WA_EXINFO-IFID = WK_IFID.
WA_EXINFO-SYSID = WK_SYSID.

* Common table acquisition process call
CALL FUNCTION 'Z_DCD_GET_FILEPARAM'
  EXPORTING
    IS_EXINFO = WA_EXINFO
    I_LANGU   = SY-LANGU
  IMPORTING
    ES_IFHEAD = WA_IFHEAD.
IF WA_IFHEAD IS INITIAL.
  MESSAGE S064(ZDCD001) WITH WK_IFID WK_SYSID
                DISPLAY LIKE C_MSGTYPE-ERROR.
  LEAVE SCREEN.
ENDIF.

* Check whether output destination can be changed
IF  CB_FOUT IS NOT INITIAL AND
  WA_IFHEAD-SENDMODE = C_SENDMODE-TAB_OP_NO_UPD_IF_FLG.
  MESSAGE S095(ZDCD001) WITH WK_IFID WK_SYSID
                DISPLAY LIKE C_MSGTYPE-ERROR.
  LEAVE SCREEN.
ENDIF.

* File Path Correlation Check
IF CB_FOUT IS INITIAL.
  RETURN.
ELSE.
* File Path Correlation Check
  IF P_LOGFNM IS INITIAL AND P_FPATH IS INITIAL.
    MESSAGE S026(ZDCD001) DISPLAY LIKE C_MSGTYPE-ERROR.
    LEAVE SCREEN.
  ELSEIF P_LOGFNM IS NOT INITIAL AND P_FPATH IS NOT INITIAL.
    MESSAGE S024(ZDCD001) DISPLAY LIKE C_MSGTYPE-ERROR.
    LEAVE SCREEN.
  ENDIF.
* Output File Correlation Check
  IF P_FPATH IS INITIAL AND P_FNAME IS NOT INITIAL.
    MESSAGE S025(ZDCD001) DISPLAY LIKE C_MSGTYPE-ERROR.
    LEAVE SCREEN.
  ELSEIF P_FPATH IS NOT INITIAL AND P_FNAME IS INITIAL.
    MESSAGE S025(ZDCD001) DISPLAY LIKE C_MSGTYPE-ERROR.
    LEAVE SCREEN.
  ENDIF.
ENDIF.

ENDFORM.
*&---------------------------------------------------------------------*
*&      Form FM_SET_LBLTEXT
*&---------------------------------------------------------------------*
*&      Label Text setting
*&---------------------------------------------------------------------*
FORM FM_SET_LBLTEXT       ##CALLED.
*-----------------------------------------------------------------------
* Variable definition
*-----------------------------------------------------------------------
DATA:
  L_WK_ROLLNAME   TYPE ROLLNAME.                                        " Data element name
*-----------------------------------------------------------------------
* Work Area definition
*-----------------------------------------------------------------------
DATA:
  L_WA_RSSELTEXTS TYPE RSSELTEXTS.                                      " Texts for parameters
*-----------------------------------------------------------------------
* Internal table definition
*-----------------------------------------------------------------------
DATA:
  L_IT_RSSELTEXTS TYPE TABLE OF RSSELTEXTS.                             "Texts for parameters

" Parameter Label acquisition
" Interface ID
L_WK_ROLLNAME = C_ROLLNAME-IFID.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WA_RSSELTEXTS-TEXT.
L_WA_RSSELTEXTS-NAME = C_SEL_FIELD-P_IFID.
L_WA_RSSELTEXTS-KIND = C_SEL_TYPE.
APPEND L_WA_RSSELTEXTS TO L_IT_RSSELTEXTS.
CLEAR L_WA_RSSELTEXTS.

" System ID
L_WK_ROLLNAME = C_ROLLNAME-SYSID.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WA_RSSELTEXTS-TEXT.
L_WA_RSSELTEXTS-NAME = C_SEL_FIELD-P_SYSID.
L_WA_RSSELTEXTS-KIND = C_SEL_TYPE.
APPEND L_WA_RSSELTEXTS TO L_IT_RSSELTEXTS.
CLEAR L_WA_RSSELTEXTS.

" File output destination change
L_WK_ROLLNAME = C_ROLLNAME-FOP_DESTCHG.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WA_RSSELTEXTS-TEXT.
L_WA_RSSELTEXTS-NAME = C_SEL_FIELD-CB_FOUT.
L_WA_RSSELTEXTS-KIND = C_SEL_TYPE.
APPEND L_WA_RSSELTEXTS TO L_IT_RSSELTEXTS.
CLEAR L_WA_RSSELTEXTS.

" Logical File Name
L_WK_ROLLNAME = C_ROLLNAME-LOG_FNAME.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WA_RSSELTEXTS-TEXT.
L_WA_RSSELTEXTS-NAME = C_SEL_FIELD-P_LOGFNM.
L_WA_RSSELTEXTS-KIND = C_SEL_TYPE.
APPEND L_WA_RSSELTEXTS TO L_IT_RSSELTEXTS.
CLEAR L_WA_RSSELTEXTS.

" Output File Path
L_WK_ROLLNAME = C_ROLLNAME-OP_FPATHN.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WA_RSSELTEXTS-TEXT.
L_WA_RSSELTEXTS-NAME = C_SEL_FIELD-P_FPATH.
L_WA_RSSELTEXTS-KIND = C_SEL_TYPE.
APPEND L_WA_RSSELTEXTS TO L_IT_RSSELTEXTS.
CLEAR L_WA_RSSELTEXTS.

" Output File Name
L_WK_ROLLNAME = C_ROLLNAME-OP_FNAME.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WA_RSSELTEXTS-TEXT.
L_WA_RSSELTEXTS-NAME = C_SEL_FIELD-P_FNAME.
L_WA_RSSELTEXTS-KIND = C_SEL_TYPE.
APPEND L_WA_RSSELTEXTS TO L_IT_RSSELTEXTS.
CLEAR L_WA_RSSELTEXTS.

" Text update
CALL FUNCTION 'SELECTION_TEXTS_MODIFY'
  EXPORTING
    PROGRAM                           = SY-REPID
  TABLES
    SELTEXTS                          = L_IT_RSSELTEXTS
  EXCEPTIONS
    PROGRAM_NOT_FOUND                 = 1
    PROGRAM_CANNOT_BE_GENERATED       = 2
    OTHERS                            = 3.
IF SY-SUBRC <> 0.
  MESSAGE S152(ZDCD001) DISPLAY LIKE C_MSGTYPE-ERROR.
  LEAVE SCREEN.
ENDIF.

" Frame Text setting
L_WK_ROLLNAME = C_ROLLNAME-FRM_TXT.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WA_RSSELTEXTS-TEXT.

WA_TITLE = L_WA_RSSELTEXTS-TEXT.

ENDFORM.
*&---------------------------------------------------------------------*
*&      Form FM_GET_LBLTEXT
*&---------------------------------------------------------------------*
*&      Label Text acquisition
*&---------------------------------------------------------------------*
*&      -->  V_ROLLNAME            Data Element Name
*&      <--> V_LBLTXT              Label Text
*&---------------------------------------------------------------------*
FORM FM_GET_LBLTEXT  USING V_ROLLNAME TYPE ROLLNAME
                  CHANGING V_LBLTXT   TYPE RSSELTEXT.
" Element Text Acquisition
SELECT SINGLE SCRTEXT_M
  FROM DD04T
  INTO V_LBLTXT
 WHERE ROLLNAME = V_ROLLNAME
   AND DDLANGUAGE = SY-LANGU
   AND AS4LOCAL = C_ACT_STAT       ##WARN_OK.

ENDFORM.
*&---------------------------------------------------------------------*
*&      Form FM_COMMON_INT
*&---------------------------------------------------------------------*
*&      Initial Process
*&---------------------------------------------------------------------*
FORM FM_COMMON_INT         ##CALLED.
*	Language setting
IF WA_IFHEAD-SPRAS IS NOT INITIAL.
  SET LOCALE LANGUAGE WA_IFHEAD-SPRAS.
ENDIF.
ENDFORM.
*&---------------------------------------------------------------------*
*&      Form FM_COMMON_MAIN
*&---------------------------------------------------------------------*
*&      Common process
*&---------------------------------------------------------------------*
*&      --> V_IT_OPTRG_DATA       Output target data
*&      --> V_IT_SRCH_KEY_INFO    Search Key Informatio
*&      --> V_IT_PROC_RESULT      Processing Result
*&---------------------------------------------------------------------*
FORM FM_COMMON_MAIN USING V_IT_OPTRG_DATA     TYPE STANDARD TABLE
                          V_IT_SRCH_KEY_INFO  TYPE STANDARD TABLE
*008(MOD)↓------------------------------------------------
*                          V_IT_PROC_RESULT    TYPE ZDCD_ERRIFOP_ST01. ##CALLED
                          V_IT_PROC_RESULT    TYPE ZDCD_ERRIFOP_ST01 ##CALLED

                          V_IS_DATANUM        TYPE ZDCD_DATANUM_S01.
*008(MOD)↑------------------------------------------------
*-----------------------------------------------------------------------
* Variable definition
*-----------------------------------------------------------------------
DATA:
  L_WK_GUID        TYPE ZDCDEGUID,                                      " GUID
  L_WK_OP_FPATH    TYPE ZDCDEFILEPATH,                                  " Output File Path
  L_WK_NO_ITM_PROC TYPE INT4,                                           " No. of items processed
  L_WK_NO_SUCCESS  TYPE INT4,                                           " No. of successes
  L_WK_NO_FAILURE  TYPE INT4.                                           " No. of failure

"	Processing Result Judgement
*005(DEL)↓--------------------------------------------------
*IF V_IT_PROC_RESULT IS INITIAL.
*005(DEL)↑--------------------------------------------------
*	Call Output process
  PERFORM FM_OUTPUT_DATA  USING V_IT_OPTRG_DATA
                                V_IT_SRCH_KEY_INFO
*008(ADD)↓------------------------------------------------
                                V_IS_DATANUM
*008(ADD)↑------------------------------------------------
                       CHANGING L_WK_GUID
                                L_WK_OP_FPATH
                                L_WK_NO_ITM_PROC
                                L_WK_NO_SUCCESS
                                L_WK_NO_FAILURE
                                V_IT_PROC_RESULT.
*005(DEL)↓--------------------------------------------------
*ENDIF.
*005(DEL)↑--------------------------------------------------
*	Call Processing result output process
  PERFORM FM_OUTPUT_LOG   USING L_WK_GUID
                       CHANGING V_IT_PROC_RESULT.

*	Call ALV Result screen output process
  PERFORM FM_ALV_DISPLAY  USING L_WK_GUID
                                L_WK_OP_FPATH
                                L_WK_NO_ITM_PROC
                                L_WK_NO_SUCCESS
                                L_WK_NO_FAILURE
                                V_IT_PROC_RESULT.
ENDFORM.
*&---------------------------------------------------------------------*
*&      Form FM_OUTPUT_DATA
*&---------------------------------------------------------------------*
*&      Output process
*&---------------------------------------------------------------------*
*&      -->  V_IT_OPTRG_DATA        Output target data
*&      -->  V_IT_SRCH_KEY_INFO     Search Key Informatio
*&      <--> V_ES_GUID              GUID
*&      <--> V_ES_OP_FPATH          Output File Path
*&      <--> V_ES_NO_ITM_PROC       No. of items processed
*&      <--> V_ES_NO_SUCCESS        No. of successes
*&      <--> V_ES_NO_FAILURE        No. of failure
*&      <--> V_ET_PROC_RESULT       Processing result
*&---------------------------------------------------------------------*
FORM FM_OUTPUT_DATA   USING V_IT_OPTRG_DATA     TYPE STANDARD TABLE
                            V_IT_SRCH_KEY_INFO  TYPE STANDARD TABLE
*008(ADD)↓------------------------------------------------
                            V_IS_DATANUM        TYPE ZDCD_DATANUM_S01
*008(ADD)↑------------------------------------------------
                   CHANGING V_ES_GUID           TYPE ZDCDEGUID
                            V_ES_OP_FPATH       TYPE ZDCDEFILEPATH
                            V_ES_NO_ITM_PROC    TYPE INT4
                            V_ES_NO_SUCCESS     TYPE INT4
                            V_ES_NO_FAILURE     TYPE INT4
                            V_ET_PROC_RESULT    TYPE ZDCD_ERRIFOP_ST01.
*-----------------------------------------------------------------------
* Variable definition
*-----------------------------------------------------------------------
DATA:
  L_WK_INDEX         TYPE I.                                            " Key index
*-----------------------------------------------------------------------
* Work Area definition
*-----------------------------------------------------------------------
DATA:
  L_WA_FILEOPT_S01   TYPE ZDCD_FILEOPT_S01,                             " File options
  L_WA_PROC_RESULT   TYPE ZDCD_ERRIFOP_S01.                             " Error structure for transmission
*-----------------------------------------------------------------------
* Internal table definition
*-----------------------------------------------------------------------
DATA:
  L_IT_ERR_MSG       TYPE ZDCD_REMSG_ST01.                              " Return message
*-----------------------------------------------------------------------
* Field Symbols definition
*-----------------------------------------------------------------------
FIELD-SYMBOLS:
  <L_FS_OP_TRG_KEY_ITM>  TYPE ANY,                                      " Output target key item
  <L_FS_OP_PROC_KEY_ITM> TYPE ANY,                                      " Output Processing result key item
  <L_FS_KEY_ITM_NAME>    TYPE ANY,                                      " Key item name
  <L_FS_OPTRG_DATA>      TYPE ANY,                                      " Output target data
  <FS_ERR_MSG>           TYPE ZDCD_REMSG_S01.                           " Return message

*002(DEL)↓--------------------------------------------------
* Output target data judgment
*CHECK V_IT_OPTRG_DATA IS NOT INITIAL.
*002(DEL)↑--------------------------------------------------

*	Output file option
IF CB_FOUT = ABAP_TRUE.
  L_WA_FILEOPT_S01-LOGFNAME = P_LOGFNM.
  L_WA_FILEOPT_S01-FILEPATH = P_FPATH.
  L_WA_FILEOPT_S01-FILENAME = P_FNAME.
ENDIF.

* Output process module calls
CALL FUNCTION 'Z_DCD_CREATE_OUTPUT_SEND'
  EXPORTING
    IS_EXINFO     = WA_EXINFO
    IT_DATA       = V_IT_OPTRG_DATA
    IT_SERCHKEY   = V_IT_SRCH_KEY_INFO
    IS_FILEOPT    = L_WA_FILEOPT_S01
*008(ADD)↓------------------------------------------------
    IS_DATANUM    = V_IS_DATANUM
*008(ADD)↑------------------------------------------------
*012(ADD)↓------------------------------------------------
    I_SYNC_COMMIT = FLG_COMMIT_SYNC
*012(ADD)↑------------------------------------------------
  IMPORTING
    E_GUID        = V_ES_GUID
    E_FILEPATH    = V_ES_OP_FPATH
    E_NUM_OUT     = V_ES_NO_ITM_PROC
    E_NUM_SUCCESS = V_ES_NO_SUCCESS
    E_NUM_ERROR   = V_ES_NO_FAILURE
    ET_ERRMSG     = L_IT_ERR_MSG
  EXCEPTIONS
    INPUT_ERROR   = 1
    CONVERT_ERROR = 2
    OUTPUT_ERROR  = 3
    UPDATE_ERROR  = 4
    GETDATA_ERROR = 5
    OTHERS        = 6.
IF SY-SUBRC <> 0.
*012(ADD)↓------------------------------------------------
  IF FLG_COMMIT_SYNC = ABAP_ON.
    ROLLBACK WORK.
  ENDIF.
*012(ADD)↑------------------------------------------------

* Output process error message
  LOOP AT L_IT_ERR_MSG ASSIGNING <FS_ERR_MSG>.
* Variable initialization
    CLEAR:
      L_WK_INDEX,
      L_WA_PROC_RESULT.
    UNASSIGN:
      <L_FS_OPTRG_DATA>.
* Read output target data
    READ TABLE V_IT_OPTRG_DATA ASSIGNING <L_FS_OPTRG_DATA>
                                   INDEX <FS_ERR_MSG>-LINE.
    IF SY-SUBRC = 0.
* Output key item setting
      DO.
        L_WK_INDEX = L_WK_INDEX + 1.
        UNASSIGN:
          <L_FS_KEY_ITM_NAME>,
          <L_FS_OP_TRG_KEY_ITM>,
          <L_FS_OP_PROC_KEY_ITM>.

        ASSIGN COMPONENT L_WK_INDEX OF STRUCTURE WA_IFHEAD-OUTKEY
                                              TO <L_FS_KEY_ITM_NAME>.
        IF <L_FS_KEY_ITM_NAME> IS ASSIGNED.
          ASSIGN COMPONENT <L_FS_KEY_ITM_NAME>
            OF STRUCTURE <L_FS_OPTRG_DATA> TO <L_FS_OP_TRG_KEY_ITM>.
          IF <L_FS_OP_TRG_KEY_ITM> IS ASSIGNED.
            ASSIGN COMPONENT L_WK_INDEX OF STRUCTURE
                          L_WA_PROC_RESULT TO <L_FS_OP_PROC_KEY_ITM>.
            IF <L_FS_OP_PROC_KEY_ITM> IS ASSIGNED.
              <L_FS_OP_PROC_KEY_ITM> = <L_FS_OP_TRG_KEY_ITM>.
            ENDIF.
          ENDIF.
        ELSE.
          EXIT.
        ENDIF.
      ENDDO.
    ENDIF.
* Error content setting
    L_WA_PROC_RESULT-ERRMSG = <FS_ERR_MSG>-MSGTXT.
* 010(ADD)↓------------------------------------------------
    L_WA_PROC_RESULT-MSGID  = <FS_ERR_MSG>-MSGID.
    L_WA_PROC_RESULT-MSGTY  = <FS_ERR_MSG>-MSGTY.
    L_WA_PROC_RESULT-MSGNO  = <FS_ERR_MSG>-MSGNO.
    L_WA_PROC_RESULT-MSGV1  = <FS_ERR_MSG>-MSGV1.
    L_WA_PROC_RESULT-MSGV2  = <FS_ERR_MSG>-MSGV2.
    L_WA_PROC_RESULT-MSGV3  = <FS_ERR_MSG>-MSGV3.
    L_WA_PROC_RESULT-MSGV4  = <FS_ERR_MSG>-MSGV4.
* 010(ADD)↑------------------------------------------------
* Data creation
    APPEND L_WA_PROC_RESULT TO V_ET_PROC_RESULT.
  ENDLOOP.
ENDIF.

*011(ADD)↓------------------------------------------------
IF V_ES_GUID IS INITIAL.
  TRY.
    CALL METHOD CL_SYSTEM_UUID=>IF_SYSTEM_UUID_STATIC~CREATE_UUID_C32
      RECEIVING
        UUID = V_ES_GUID.
  CATCH CX_UUID_ERROR ##NO_HANDLER.
  ENDTRY.
ENDIF.
*011(ADD)↑------------------------------------------------

ENDFORM.
*&---------------------------------------------------------------------*
*&      Form FM_OUTPUT_LOG
*&---------------------------------------------------------------------*
*&      Processing result output
*&---------------------------------------------------------------------*
*&      --> V_GUID                  GUID
*&      --> V_IT_PROC_RESULT        Processing result
*&---------------------------------------------------------------------*
FORM FM_OUTPUT_LOG  USING V_GUID            TYPE ZDCDEGUID
                 CHANGING V_IT_PROC_RESULT  TYPE ZDCD_ERRIFOP_ST01.
*-----------------------------------------------------------------------
* Variable definition
*-----------------------------------------------------------------------
DATA:
  L_WA_BAL_S_CONT       TYPE BAL_S_CONT,                                " Application Log: Context
  L_WA_BAL_S_LOG        TYPE BAL_S_LOG,                                 " Application Log: Log header data
  L_WA_CONTEXT          TYPE ZDCD_CONTEXT_S01,                          " Context value structure
  L_WA_OBJECT	          TYPE BALOBJ_D     ##NEEDED,                     " Regulated object
  L_WA_SUBOBJECT        TYPE BALSUBOBJ    ##NEEDED.                     " Regulated sub-object
*-----------------------------------------------------------------------
* Work Area definition
*-----------------------------------------------------------------------
DATA:
  L_WK_EXT_NUM          TYPE STRING,                                    " External Number
  L_WK_LINE_NO          TYPE I,                                         " Line Number
* 009(DEL)↓------------------------------------------------
* 007(MOD)↓------------------------------------------------
*  L_WK_MSG              TYPE SYMSGV,                                    " Message text
*  L_WK_MSG              TYPE MSGTXT_LONG,                               " Message text
* 007(MOD)↑------------------------------------------------
* 007(ADD)↓------------------------------------------------
*  L_WK_MSG1             TYPE SYMSGV,                                    " Message text1
*  L_WK_MSG2             TYPE SYMSGV,                                    " Message text2
*  L_WK_MSG3             TYPE SYMSGV,                                    " Message text3
*  L_WK_MSG4             TYPE SYMSGV,                                    " Message text4
* 007(ADD)↑------------------------------------------------
* 009(DEL)↑------------------------------------------------
  L_WK_VALUE_TABLE      TYPE ZDCD0003,                                  " Common Parameters values
  L_WA_PROC_RESULT      TYPE ZDCD_ERRIFOP_S01,                          " Error structure for transmission
  L_REF_APPLICATION_LOG TYPE REF TO ZCL_DCD_APPLICATION_LOG.            " Application log
*-----------------------------------------------------------------------
* Internal table definitions
*-----------------------------------------------------------------------
DATA:
  L_IT_VALUE_TABLE  TYPE  ZDCD0003_ST01.                                " Common parameter 03
*-----------------------------------------------------------------------
* Field Symbol definitions
*-----------------------------------------------------------------------
FIELD-SYMBOLS:
  <FS_PROC_RESULT>      TYPE ZDCD_ERRIFOP_S01.                          " Error structure for transmission

" Application Log Parameter Setting
IF WA_IFHEAD-OBJECT IS INITIAL AND WA_IFHEAD-SUBOBJECT IS INITIAL.

" Common Parameter Acquisition
  CALL FUNCTION 'Z_DCD_COMMON_PARAMS'
    EXPORTING
      I_PROGRAM_ID             = C_PROGRAM_ID
      I_PARAM_ID               = C_PARAM_ID
    IMPORTING
      ET_VALUE_TABLE           = L_IT_VALUE_TABLE
    EXCEPTIONS
      INVALID_PROGRAM_ID       = 1
      INVALID_PARAM_ID         = 2
      DATA_NOT_FOUND           = 3
      DATA_TYPES_ERROR         = 4
      OTHERS                   = 5.
" Object and Sub-Object setting2
  IF SY-SUBRC = 0.
    READ TABLE L_IT_VALUE_TABLE INTO L_WK_VALUE_TABLE INDEX 1.
    IF SY-SUBRC IS INITIAL.
      L_WA_OBJECT     = L_WK_VALUE_TABLE-VALUE1.
      L_WA_SUBOBJECT  = L_WK_VALUE_TABLE-VALUE2.
    ENDIF.
  ELSE.
    L_WA_OBJECT     = C_REG_OBJECT.
    L_WA_SUBOBJECT  = C_REG_SUBOBJECT.
  ENDIF.
ELSE.
  L_WA_OBJECT     = WA_IFHEAD-OBJECT.
  L_WA_SUBOBJECT  = WA_IFHEAD-SUBOBJECT.
ENDIF.
LOOP AT V_IT_PROC_RESULT ASSIGNING <FS_PROC_RESULT>.
* External numbering
  CONCATENATE V_GUID
              <FS_PROC_RESULT>-KEYVAL1
              <FS_PROC_RESULT>-KEYVAL2
              <FS_PROC_RESULT>-KEYVAL3
              <FS_PROC_RESULT>-KEYVAL4
              <FS_PROC_RESULT>-KEYVAL5
              <FS_PROC_RESULT>-KEYVAL6
              <FS_PROC_RESULT>-KEYVAL7
              <FS_PROC_RESULT>-KEYVAL8
              <FS_PROC_RESULT>-KEYVAL9
              <FS_PROC_RESULT>-KEYVAL10
              INTO L_WK_EXT_NUM.
* 006(ADD)↓------------------------------------------------
  CONDENSE L_WK_EXT_NUM.
* 006(ADD)↑------------------------------------------------

* External number judgment
* 006(MOD)↓------------------------------------------------
*  AT NEW KEYVAL1 .
  AT NEW KEYVAL10.
* 006(MOD)↑------------------------------------------------
* Log Header Creation
* Count up Line Number
    L_WK_LINE_NO              = L_WK_LINE_NO + 1.
* Context Value Edit
    L_WA_CONTEXT-IFID         = WK_IFID.
    L_WA_CONTEXT-SYSID        = WK_SYSID.
    L_WA_CONTEXT-GUID         = V_GUID.
    L_WA_CONTEXT-LINE         = L_WK_LINE_NO.
* Context Edit
    L_WA_BAL_S_CONT-TABNAME   = C_CONTEXT_S01.
    L_WA_BAL_S_CONT-VALUE     = L_WA_CONTEXT.
* Creates Structure: Log header.
    L_WA_BAL_S_LOG-EXTNUMBER  = L_WK_EXT_NUM.
    L_WA_BAL_S_LOG-OBJECT     = L_WA_OBJECT.
    L_WA_BAL_S_LOG-SUBOBJECT  = L_WA_SUBOBJECT.
    L_WA_BAL_S_LOG-ALDATE     = SY-DATUM.
    L_WA_BAL_S_LOG-ALTIME     = SY-UZEIT.
    L_WA_BAL_S_LOG-ALUSER     = SY-UNAME.
    L_WA_BAL_S_LOG-ALTCODE    = SY-TCODE.
    L_WA_BAL_S_LOG-ALPROG     = SY-CPROG.
    L_WA_BAL_S_LOG-CONTEXT    = L_WA_BAL_S_CONT.
* Log interface generation
    CREATE OBJECT L_REF_APPLICATION_LOG
      EXPORTING
        IS_LOG_HEADER = L_WA_BAL_S_LOG.
  ENDAT .
*	Add Message
* Edit Message

* 009(DEL)↓------------------------------------------------
*   L_WK_MSG = <FS_PROC_RESULT>-ERRMSG.
* 007(ADD)↓------------------------------------------------
*  L_WK_MSG1 = L_WK_MSG+0(50).
*  L_WK_MSG2 = L_WK_MSG+50(50).
*  L_WK_MSG3 = L_WK_MSG+100(50).
*  L_WK_MSG4 = L_WK_MSG+150(50).
* 007(ADD)↑------------------------------------------------
* 009(DEL)↑------------------------------------------------

* Message adding process call
  TRY.
* 009(MOD)↓------------------------------------------------
*    CALL METHOD L_REF_APPLICATION_LOG->MESSAGE_ADD
*      EXPORTING
*        I_MSGTY    = C_MSGTYPE-ERROR
*        I_MSGID    = 'ZDCD001'
* 007(MOD)↓------------------------------------------------
*        I_MSGNO    = '000'
*        I_MSGV1    = L_WK_MSG
*        I_MSGNO    = '161'
*        I_MSGV1    = L_WK_MSG1
*        I_MSGV2    = L_WK_MSG2
*        I_MSGV3    = L_WK_MSG3
*        I_MSGV4    = L_WK_MSG4
* 007(MOD)↑------------------------------------------------
*        IS_CONTEXT = L_WA_BAL_S_CONT.
*   Message Data Check
      IF <FS_PROC_RESULT>-MSGTY IS NOT INITIAL AND <FS_PROC_RESULT>-MSGID IS NOT INITIAL
        AND  <FS_PROC_RESULT>-MSGNO IS NOT INITIAL.
        CALL METHOD L_REF_APPLICATION_LOG->MESSAGE_ADD
          EXPORTING
            I_MSGTY    = <FS_PROC_RESULT>-MSGTY
            I_MSGID    = <FS_PROC_RESULT>-MSGID
            I_MSGNO    = <FS_PROC_RESULT>-MSGNO
            I_MSGV1    = <FS_PROC_RESULT>-MSGV1
            I_MSGV2    = <FS_PROC_RESULT>-MSGV2
            I_MSGV3    = <FS_PROC_RESULT>-MSGV3
            I_MSGV4    = <FS_PROC_RESULT>-MSGV4
            IS_CONTEXT = L_WA_BAL_S_CONT.
     ELSE.
       CALL METHOD L_REF_APPLICATION_LOG->MESSAGE_ADD
          EXPORTING
            I_MSGTY    = C_MSGTYPE-ERROR
            I_MSGID    = 'ZDCD001'
            I_MSGNO    = '161'
            I_MSGV1    = <FS_PROC_RESULT>-ERRMSG+0(50)
            I_MSGV2    = <FS_PROC_RESULT>-ERRMSG+50(50)
            I_MSGV3    = <FS_PROC_RESULT>-ERRMSG+100(50)
            I_MSGV4    = <FS_PROC_RESULT>-ERRMSG+150(50)
            IS_CONTEXT = L_WA_BAL_S_CONT.
     ENDIF.
* 009(MOD)↑------------------------------------------------
    CATCH ZCX_DCD_APPLICATION_LOG   ##NO_HANDLER.
      CLEAR:
        L_WA_PROC_RESULT.
      MESSAGE E063(ZDCD001) INTO L_WA_PROC_RESULT-ERRMSG.
      APPEND L_WA_PROC_RESULT TO V_IT_PROC_RESULT.
      RETURN.
  ENDTRY.
* 006(MOD)↓------------------------------------------------
*  AT END OF KEYVAL1 .
  AT END OF KEYVAL10.
* 006(MOD)↑------------------------------------------------
* Save Table
    TRY.
* Log data saving process call
      CALL METHOD L_REF_APPLICATION_LOG->DB_SAVE
        EXPORTING
          I_IN_UPDATE_TASK = ABAP_FALSE.
* Log release process call
      CALL METHOD L_REF_APPLICATION_LOG->REFRESH.
    CATCH ZCX_DCD_APPLICATION_LOG   ##NO_HANDLER.
      CLEAR:
        L_WA_PROC_RESULT.
      MESSAGE E063(ZDCD001) INTO L_WA_PROC_RESULT-ERRMSG.
* 010(ADD)↓------------------------------------------------
      L_WA_PROC_RESULT-MSGID = 'ZDCD001'.
      L_WA_PROC_RESULT-MSGTY = 'E'.
      L_WA_PROC_RESULT-MSGNO = 063.
* 010(ADD)↑------------------------------------------------
      APPEND L_WA_PROC_RESULT TO V_IT_PROC_RESULT.
      RETURN.
    ENDTRY.
  ENDAT .
ENDLOOP.

ENDFORM.
*&---------------------------------------------------------------------*
*&      Form FM_ALV_DISPLAY
*&---------------------------------------------------------------------*
*&      ALV Result screen output
*&---------------------------------------------------------------------*
*&      --> V_GUID                  GUID
*&      --> V_OP_FPATH              Output File Path
*&      --> V_NO_ITM_PROC           No. of items processed
*&      --> V_NO_SUCCESS            No. of successes
*&      --> V_NO_FAILURE            No. of failure
*&      --> V_IT_PROC_RESULT        Processing result
*&---------------------------------------------------------------------*
FORM FM_ALV_DISPLAY USING V_GUID            TYPE ZDCDEGUID
                          V_OP_FPATH        TYPE ZDCDEFILEPATH
                          V_NO_ITM_PROC     TYPE INT4
                          V_NO_SUCCESS      TYPE INT4
                          V_NO_FAILURE      TYPE INT4
                          V_IT_PROC_RESULT  TYPE ZDCD_ERRIFOP_ST01.
*-----------------------------------------------------------------------
* Variable definition
*-----------------------------------------------------------------------
DATA:
  L_WK_NO_OF_DIGIT TYPE I,                                              " No. of digits
  L_WK_FIRST_DIGIT TYPE I,                                              " First digit
  L_WK_KEY(20)     TYPE C,                                              " Fey field
  L_WK_ROLLNAME    TYPE ROLLNAME,                                       " Data element name
  L_WK_LBLTXT      TYPE RSSELTEXT,                                      " Label text
  L_WK_ALV_ITM_TXT TYPE RSSELTEXT.                                      " Label text
*-----------------------------------------------------------------------
* Work Area definition
*-----------------------------------------------------------------------
DATA:
  L_WA_LAYOUT      TYPE SLIS_LAYOUT_ALV,                                " ALV Layout
  L_WA_COMM        TYPE SLIS_LISTHEADER.                                " ALV Header commentary
*-----------------------------------------------------------------------
* Internal table definition
*-----------------------------------------------------------------------
DATA:
  L_IT_FIELDCAT    TYPE SLIS_T_FIELDCAT_ALV.                            " ALV Field catalog
* 004(ADD)↓------------------------------------------------
DATA:
  L_IT_DD03L       TYPE TAT_DD03L.
* 004(ADD)↑------------------------------------------------
*-----------------------------------------------------------------------
* Field Symbols definition
*-----------------------------------------------------------------------
FIELD-SYMBOLS:
  <L_FS_FIELDCAT> TYPE  SLIS_FIELDCAT_ALV.                              " ALV Field catalog

* ALV Layout Settings
L_WA_LAYOUT-COLWIDTH_OPTIMIZE = ABAP_TRUE.

* ALV header information setting

* GUID
L_WK_ROLLNAME   = C_ROLLNAME-GUID.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WK_LBLTXT.

L_WA_COMM-TYP   = C_LISTHEAD_TYP.
L_WA_COMM-KEY   = L_WK_LBLTXT.
L_WA_COMM-INFO  = V_GUID.
APPEND L_WA_COMM TO IT_COMM.
CLEAR:
  L_WA_COMM,
  L_WK_LBLTXT.

* Output File Path
* Acquire number of degit for Parameter: Output File Path and
*         store it to Variable: Number of digit
L_WK_NO_OF_DIGIT  = STRLEN( V_OP_FPATH ).
" Initialize Variable: First digit number
CLEAR L_WK_FIRST_DIGIT.

L_WK_ROLLNAME     = C_ROLLNAME-OP_FPATH.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WK_LBLTXT.
* Number or digit judgement process
DO.
  IF L_WK_FIRST_DIGIT >= L_WK_NO_OF_DIGIT.
    EXIT.
  ENDIF.

  IF L_WK_FIRST_DIGIT = 0.
    L_WK_KEY = L_WK_LBLTXT.
  ELSE.
    CLEAR L_WK_KEY.
  ENDIF.

  L_WA_COMM-TYP   = C_LISTHEAD_TYP.
  L_WA_COMM-KEY   = L_WK_KEY.
  L_WA_COMM-INFO  = V_OP_FPATH+L_WK_FIRST_DIGIT(C_FLD_INDEX).
  APPEND L_WA_COMM TO IT_COMM.
  CLEAR L_WA_COMM.

  L_WK_FIRST_DIGIT = L_WK_FIRST_DIGIT + C_FLD_INDEX.
ENDDO.
CLEAR:
  L_WK_LBLTXT.

* No. of items to be processed
L_WK_ROLLNAME   = C_ROLLNAME-NO_ITM_PROC.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WK_LBLTXT.
CONCATENATE L_WK_LBLTXT C_SEP_COLON INTO L_WK_ALV_ITM_TXT.
L_WA_COMM-TYP   = C_LISTHEAD_TYP.
L_WA_COMM-KEY   = L_WK_ALV_ITM_TXT.
WRITE V_NO_ITM_PROC TO L_WA_COMM-INFO.
APPEND L_WA_COMM TO IT_COMM.
CLEAR:
  L_WA_COMM,
  L_WK_LBLTXT,
  L_WK_ALV_ITM_TXT.

* No. of successes
L_WK_ROLLNAME   = C_ROLLNAME-NO_SUCC.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WK_LBLTXT.
CONCATENATE L_WK_LBLTXT C_SEP_COLON INTO L_WK_ALV_ITM_TXT.
L_WA_COMM-TYP   = C_LISTHEAD_TYP.
L_WA_COMM-KEY   = L_WK_ALV_ITM_TXT.
WRITE V_NO_SUCCESS TO L_WA_COMM-INFO.
APPEND L_WA_COMM TO IT_COMM.
CLEAR:
  L_WA_COMM,
  L_WK_LBLTXT,
  L_WK_ALV_ITM_TXT.

* No. of failures
L_WK_ROLLNAME   = C_ROLLNAME-NO_FAIL.
PERFORM FM_GET_LBLTEXT  USING L_WK_ROLLNAME
                     CHANGING L_WK_LBLTXT.
CONCATENATE L_WK_LBLTXT C_SEP_COLON INTO L_WK_ALV_ITM_TXT.
L_WA_COMM-TYP   = C_LISTHEAD_TYP.
L_WA_COMM-KEY   = L_WK_ALV_ITM_TXT.
WRITE V_NO_FAILURE TO L_WA_COMM-INFO.
APPEND L_WA_COMM TO IT_COMM.
CLEAR:
  L_WA_COMM,
  L_WK_LBLTXT,
  L_WK_ALV_ITM_TXT.

* Initialize
CLEAR:
  L_IT_FIELDCAT.
* Field Catalog Creation
CALL FUNCTION 'REUSE_ALV_FIELDCATALOG_MERGE'
  EXPORTING
    I_PROGRAM_NAME         = SY-REPID
    I_STRUCTURE_NAME       = C_ALV_S01
  CHANGING
    CT_FIELDCAT            = L_IT_FIELDCAT
  EXCEPTIONS
    INCONSISTENT_INTERFACE = 1
    PROGRAM_ERROR          = 2
    OTHERS                 = 3.
IF SY-SUBRC = 0.

* 004(ADD)↓------------------------------------------------
  SELECT FIELDNAME
         ROLLNAME
    FROM DD03L
    INTO TABLE L_IT_DD03L
   WHERE TABNAME = WA_IFHEAD-STRNAME
     AND AS4LOCAL = C_ACT_STAT.
* 004(ADD)↑------------------------------------------------

* Item display setting
  LOOP AT L_IT_FIELDCAT ASSIGNING <L_FS_FIELDCAT>.

    CASE <L_FS_FIELDCAT>-FIELDNAME.
      WHEN C_FIELDNAME-KEYVAL1.
        IF WA_IFHEAD-KEYVAL1 IS INITIAL .
          <L_FS_FIELDCAT>-NO_OUT = ABAP_TRUE.
* 004(ADD)↓------------------------------------------------
        ELSE.
          PERFORM FM_GET_ALV_LABEL USING L_IT_DD03L
                                         WA_IFHEAD-KEYVAL1
                                CHANGING <L_FS_FIELDCAT>-ROLLNAME
                                         <L_FS_FIELDCAT>-REPTEXT_DDIC
                                         <L_FS_FIELDCAT>-SELTEXT_S
                                         <L_FS_FIELDCAT>-SELTEXT_M
                                         <L_FS_FIELDCAT>-SELTEXT_L.
* 004(ADD)↑------------------------------------------------
        ENDIF.
      WHEN C_FIELDNAME-KEYVAL2.
        IF WA_IFHEAD-KEYVAL2 IS INITIAL .
          <L_FS_FIELDCAT>-NO_OUT = ABAP_TRUE.
* 004(ADD)↓------------------------------------------------
        ELSE.
          PERFORM FM_GET_ALV_LABEL USING L_IT_DD03L
                                         WA_IFHEAD-KEYVAL2
                                CHANGING <L_FS_FIELDCAT>-ROLLNAME
                                         <L_FS_FIELDCAT>-REPTEXT_DDIC
                                         <L_FS_FIELDCAT>-SELTEXT_S
                                         <L_FS_FIELDCAT>-SELTEXT_M
                                         <L_FS_FIELDCAT>-SELTEXT_L.
* 004(ADD)↑------------------------------------------------
        ENDIF.
      WHEN C_FIELDNAME-KEYVAL3.
        IF WA_IFHEAD-KEYVAL3 IS INITIAL .
          <L_FS_FIELDCAT>-NO_OUT = ABAP_TRUE.
* 004(ADD)↓------------------------------------------------
        ELSE.
          PERFORM FM_GET_ALV_LABEL USING L_IT_DD03L
                                         WA_IFHEAD-KEYVAL3
                                CHANGING <L_FS_FIELDCAT>-ROLLNAME
                                         <L_FS_FIELDCAT>-REPTEXT_DDIC
                                         <L_FS_FIELDCAT>-SELTEXT_S
                                         <L_FS_FIELDCAT>-SELTEXT_M
                                         <L_FS_FIELDCAT>-SELTEXT_L.
* 004(ADD)↑------------------------------------------------
        ENDIF.
      WHEN C_FIELDNAME-KEYVAL4.
        IF WA_IFHEAD-KEYVAL4 IS INITIAL .
          <L_FS_FIELDCAT>-NO_OUT = ABAP_TRUE.
* 004(ADD)↓------------------------------------------------
        ELSE.
          PERFORM FM_GET_ALV_LABEL USING L_IT_DD03L
                                         WA_IFHEAD-KEYVAL4
                                CHANGING <L_FS_FIELDCAT>-ROLLNAME
                                         <L_FS_FIELDCAT>-REPTEXT_DDIC
                                         <L_FS_FIELDCAT>-SELTEXT_S
                                         <L_FS_FIELDCAT>-SELTEXT_M
                                         <L_FS_FIELDCAT>-SELTEXT_L.
* 004(ADD)↑------------------------------------------------
        ENDIF.
      WHEN C_FIELDNAME-KEYVAL5.
        IF WA_IFHEAD-KEYVAL5 IS INITIAL .
          <L_FS_FIELDCAT>-NO_OUT = ABAP_TRUE.
* 004(ADD)↓------------------------------------------------
        ELSE.
          PERFORM FM_GET_ALV_LABEL USING L_IT_DD03L
                                         WA_IFHEAD-KEYVAL5
                                CHANGING <L_FS_FIELDCAT>-ROLLNAME
                                         <L_FS_FIELDCAT>-REPTEXT_DDIC
                                         <L_FS_FIELDCAT>-SELTEXT_S
                                         <L_FS_FIELDCAT>-SELTEXT_M
                                         <L_FS_FIELDCAT>-SELTEXT_L.
* 004(ADD)↑------------------------------------------------
        ENDIF.
      WHEN C_FIELDNAME-KEYVAL6.
        IF WA_IFHEAD-KEYVAL6 IS INITIAL .
          <L_FS_FIELDCAT>-NO_OUT = ABAP_TRUE.
* 004(ADD)↓------------------------------------------------
        ELSE.
          PERFORM FM_GET_ALV_LABEL USING L_IT_DD03L
                                         WA_IFHEAD-KEYVAL6
                                CHANGING <L_FS_FIELDCAT>-ROLLNAME
                                         <L_FS_FIELDCAT>-REPTEXT_DDIC
                                         <L_FS_FIELDCAT>-SELTEXT_S
                                         <L_FS_FIELDCAT>-SELTEXT_M
                                         <L_FS_FIELDCAT>-SELTEXT_L.
* 004(ADD)↑------------------------------------------------
        ENDIF.
      WHEN C_FIELDNAME-KEYVAL7.
        IF WA_IFHEAD-KEYVAL7 IS INITIAL .
          <L_FS_FIELDCAT>-NO_OUT = ABAP_TRUE.
* 004(ADD)↓------------------------------------------------
        ELSE.
          PERFORM FM_GET_ALV_LABEL USING L_IT_DD03L
                                         WA_IFHEAD-KEYVAL7
                                CHANGING <L_FS_FIELDCAT>-ROLLNAME
                                         <L_FS_FIELDCAT>-REPTEXT_DDIC
                                         <L_FS_FIELDCAT>-SELTEXT_S
                                         <L_FS_FIELDCAT>-SELTEXT_M
                                         <L_FS_FIELDCAT>-SELTEXT_L.
* 004(ADD)↑------------------------------------------------
        ENDIF.
      WHEN C_FIELDNAME-KEYVAL8.
        IF WA_IFHEAD-KEYVAL8 IS INITIAL .
          <L_FS_FIELDCAT>-NO_OUT = ABAP_TRUE.
* 004(ADD)↓------------------------------------------------
        ELSE.
          PERFORM FM_GET_ALV_LABEL USING L_IT_DD03L
                                         WA_IFHEAD-KEYVAL8
                                CHANGING <L_FS_FIELDCAT>-ROLLNAME
                                         <L_FS_FIELDCAT>-REPTEXT_DDIC
                                         <L_FS_FIELDCAT>-SELTEXT_S
                                         <L_FS_FIELDCAT>-SELTEXT_M
                                         <L_FS_FIELDCAT>-SELTEXT_L.
* 004(ADD)↑------------------------------------------------
        ENDIF.
      WHEN C_FIELDNAME-KEYVAL9.
        IF WA_IFHEAD-KEYVAL9 IS INITIAL .
          <L_FS_FIELDCAT>-NO_OUT = ABAP_TRUE.
* 004(ADD)↓------------------------------------------------
        ELSE.
          PERFORM FM_GET_ALV_LABEL USING L_IT_DD03L
                                         WA_IFHEAD-KEYVAL9
                                CHANGING <L_FS_FIELDCAT>-ROLLNAME
                                         <L_FS_FIELDCAT>-REPTEXT_DDIC
                                         <L_FS_FIELDCAT>-SELTEXT_S
                                         <L_FS_FIELDCAT>-SELTEXT_M
                                         <L_FS_FIELDCAT>-SELTEXT_L.
* 004(ADD)↑------------------------------------------------
        ENDIF.
      WHEN C_FIELDNAME-KEYVAL10.
        IF WA_IFHEAD-KEYVAL10 IS INITIAL .
          <L_FS_FIELDCAT>-NO_OUT = ABAP_TRUE.
* 004(ADD)↓------------------------------------------------
        ELSE.
          PERFORM FM_GET_ALV_LABEL USING L_IT_DD03L
                                         WA_IFHEAD-KEYVAL10
                                CHANGING <L_FS_FIELDCAT>-ROLLNAME
                                         <L_FS_FIELDCAT>-REPTEXT_DDIC
                                         <L_FS_FIELDCAT>-SELTEXT_S
                                         <L_FS_FIELDCAT>-SELTEXT_M
                                         <L_FS_FIELDCAT>-SELTEXT_L.
* 004(ADD)↑------------------------------------------------
        ENDIF.
* 004(ADD)↓------------------------------------------------
      WHEN C_FIELDNAME-MSGV1.
        <L_FS_FIELDCAT>-NO_OUT  = ABAP_ON.
      WHEN C_FIELDNAME-MSGV2.
        <L_FS_FIELDCAT>-NO_OUT  = ABAP_ON.
      WHEN C_FIELDNAME-MSGV3.
        <L_FS_FIELDCAT>-NO_OUT  = ABAP_ON.
      WHEN C_FIELDNAME-MSGV4.
        <L_FS_FIELDCAT>-NO_OUT  = ABAP_ON.
* 004(ADD)↑------------------------------------------------
      WHEN OTHERS.
    ENDCASE.
  ENDLOOP.
ENDIF.

* ALV Output
CALL FUNCTION 'REUSE_ALV_GRID_DISPLAY'
  EXPORTING
    I_CALLBACK_PROGRAM     = SY-REPID
    I_CALLBACK_TOP_OF_PAGE = 'FM_TOP_OF_PAGE'
    IS_LAYOUT              = L_WA_LAYOUT
    IT_FIELDCAT            = L_IT_FIELDCAT
  TABLES
    T_OUTTAB               = V_IT_PROC_RESULT
  EXCEPTIONS
    PROGRAM_ERROR          = 1
    OTHERS                 = 2.
* Processing result judgment
IF SY-SUBRC <> 0.
  MESSAGE E027(ZDCD001) WITH V_GUID.
ENDIF.

* 010(ADD)↓------------------------------------------------
IF SY-BATCH IS NOT INITIAL AND
   WA_IFHEAD-JOBERROR3 = ABAP_ON.

  READ TABLE V_IT_PROC_RESULT WITH KEY MSGTY = C_MSGTYPE-ERROR TRANSPORTING NO FIELDS.

  IF SY-SUBRC = 0.
    MESSAGE E062(ZDCD001).
  ENDIF.
ENDIF.
* 010(ADD)↑------------------------------------------------

ENDFORM.
*&---------------------------------------------------------------------*
*&      Form FM_TOP_OF_PAGE
*&---------------------------------------------------------------------*
*&      ALV Header Information setting
*&---------------------------------------------------------------------*
FORM FM_TOP_OF_PAGE     ##CALLED.
* Call Header setting module
CALL FUNCTION 'REUSE_ALV_COMMENTARY_WRITE'
  EXPORTING
    IT_LIST_COMMENTARY = IT_COMM.
ENDFORM.
* 004(ADD)↓------------------------------------------------
*&---------------------------------------------------------------------*
*& Form FM_GET_ALV_LABEL
*&---------------------------------------------------------------------*
*& ALV Label
*&---------------------------------------------------------------------*
*&      --> V_IT_DD03L         Label Table
*&      --> V_FIELDNAME        Field Name
*&      <-- V_ROLLNAME         Element
*&      <-- V_REPTEXT_DDIC     Long Text
*&      <-- V_SELTEXT_S        Short Text
*&      <-- V_SELTEXT_M        Midle Text
*&      <-- V_SELTEXT_L        Long Text
*&---------------------------------------------------------------------*
FORM FM_GET_ALV_LABEL  USING V_IT_DD03L       TYPE TAT_DD03L
                              V_FIELDNAME     TYPE ZDCDEKEYVAL1
                     CHANGING V_ROLLNAME      TYPE ROLLNAME
                              V_REPTEXT_DDIC  TYPE REPTEXT
                              V_SELTEXT_S     TYPE SCRTEXT_S
                              V_SELTEXT_M     TYPE SCRTEXT_M
                              V_SELTEXT_L     TYPE SCRTEXT_L.

  DATA:
    L_WA_DD03L     TYPE TA_DD03L,
    L_WK_REPTEXT   TYPE REPTEXT,
    L_WK_SCRTEXT_S TYPE SCRTEXT_S,
    L_WK_SCRTEXT_M TYPE SCRTEXT_M,
    L_WK_SCRTEXT_L TYPE SCRTEXT_L.

  READ TABLE V_IT_DD03L INTO L_WA_DD03L
    WITH KEY FIELDNAME =  V_FIELDNAME   ##WARN_OK.

* エレメントが取得できない場合、ラベルに項目IDを設定する
  IF SY-SUBRC <> 0.
    V_REPTEXT_DDIC = V_FIELDNAME.
    V_SELTEXT_S    = V_FIELDNAME.
    V_SELTEXT_M    = V_FIELDNAME.
    V_SELTEXT_L    = V_FIELDNAME.
    RETURN.
  ENDIF.

  SELECT SINGLE
         REPTEXT
         SCRTEXT_S
         SCRTEXT_M
         SCRTEXT_L
    INTO ( L_WK_REPTEXT, L_WK_SCRTEXT_S, L_WK_SCRTEXT_M, L_WK_SCRTEXT_L )
    FROM DD04T
   WHERE ROLLNAME   = L_WA_DD03L-ROLLNAME
     AND DDLANGUAGE = SY-LANGU
     AND AS4LOCAL   = C_ACT_STAT       ##WARN_OK.

* 取得できた場合、ラベルに取得したテキストを設定する
  IF SY-SUBRC = 0.
    V_ROLLNAME     = L_WA_DD03L-ROLLNAME.
    V_REPTEXT_DDIC = L_WK_REPTEXT.
    V_SELTEXT_S    = L_WK_SCRTEXT_S.
    V_SELTEXT_M    = L_WK_SCRTEXT_M.
    V_SELTEXT_L    = L_WK_SCRTEXT_L.
* 取得できない場合、ラベルに項目IDを設定する
  ELSE.
    V_ROLLNAME     = L_WA_DD03L-ROLLNAME.
    V_REPTEXT_DDIC = V_FIELDNAME.
    V_SELTEXT_S    = V_FIELDNAME.
    V_SELTEXT_M    = V_FIELDNAME.
    V_SELTEXT_L    = V_FIELDNAME.
  ENDIF.

ENDFORM.
* 004(ADD)↑------------------------------------------------
* 012(ADD)↓------------------------------------------------
*&---------------------------------------------------------------------*
*& Form FM_ZDCDF001_INITIALIZATION
*&---------------------------------------------------------------------*
*& 共通Include初期処理
*&---------------------------------------------------------------------*
FORM FM_ZDCDF001_INITIALIZATION .

* グローバル変数の初期化
  CLEAR:
    FLG_COMMIT_SYNC.

ENDFORM.
* 012(ADD)↑------------------------------------------------
