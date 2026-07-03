*----------------------------------------------------------------------*
***INCLUDE ZPNMB023F01.
*----------------------------------------------------------------------*
*&---------------------------------------------------------------------*
*& Form FM_ALV_DISPLAY_Z053
*&---------------------------------------------------------------------*
*& FM_COMMON_MAIN - FM_ALV_DISPLAY
*&---------------------------------------------------------------------*
*&      --> L_GUID
*&      --> L_OP_FPATH
*&      --> L_NO_ITM_PROC
*&      --> L_NO_SUCCESS
*&      --> L_NO_FAILURE
*&      --> IT_RETURN
*&---------------------------------------------------------------------*
FORM FM_ALV_DISPLAY_Z053
  USING V_GUID        TYPE ZDCDEGUID
        V_OP_FPATH    TYPE ZDCDEFILEPATH
        V_NO_ITM_PROC TYPE INT4
        V_NO_SUCCESS  TYPE INT4
        V_NO_FAILURE  TYPE INT4
        V_IT_RETURN   TYPE ZDCD_ERRIFOP_ST01.

  PERFORM FM_ALV_DISPLAY
    USING V_GUID
          V_OP_FPATH
          V_NO_ITM_PROC
          V_NO_SUCCESS
          V_NO_FAILURE
          V_IT_RETURN.
ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_CHECK_AUTH
*&---------------------------------------------------------------------*
*& 権限チェック(プラント)
*&---------------------------------------------------------------------*
*& -->  p1        text
*& <--  p2        text
*&---------------------------------------------------------------------*
FORM FM_CHECK_AUTH .

* WK
  DATA L_WA_MSGV TYPE MSGV_EXT.

* WK
  DATA L_BUKRS TYPE BUKRS.

* 004(ADD)↓------------------------------------------------
* 固定値
  CONSTANTS:
    L_C_ACTVT   TYPE ACTIV_AUTH   VALUE '01'.     "アクティビティ(登録)
* 004(ADD)↑------------------------------------------------

* 006(MOD)↓------------------------------------------------
*  SELECT SINGLE BUKRS INTO @L_BUKRS
** 005(MOD)↓------------------------------------------------
**    FROM T001W INNER JOIN T001K
*    FROM T001W INNER JOIN T001K   "#EC CI_BUFFJOIN
** 005(MOD)↑------------------------------------------------
*      ON T001W~BWKEY = T001K~BWKEY
*    WHERE T001W~WERKS = @P_WERKS  ##WARN_OK.

  SELECT BUKRS INTO @L_BUKRS
    FROM T001W INNER JOIN T001K   "#EC CI_BUFFJOIN
      ON T001W~BWKEY = T001K~BWKEY
    UP TO 1 ROWS
    WHERE T001W~WERKS = @P_WERKS
    ORDER BY BUKRS.
  ENDSELECT.
* 006(MOD)↑------------------------------------------------

  IF SY-SUBRC = 0.
    AUTHORITY-CHECK OBJECT WK_OBJCT
      ID 'BUKRS' FIELD L_BUKRS
* 004(ADD)↓------------------------------------------------
      ID 'ACTVT' FIELD L_C_ACTVT.
* 004(ADD)↑------------------------------------------------
    IF SY-SUBRC <> 0.
* 004(MOD)↓------------------------------------------------
*     オンライン実行の場合
      IF SY-BATCH IS INITIAL.
        L_WA_MSGV = L_C_ACTVT.
        MESSAGE ID 'ZPNM001' TYPE C_MSGTY-ERROR NUMBER '638'
* 006(MOD)↓------------------------------------------------
*          WITH L_BUKRS L_WA_MSGV  ##MG_MISSING.
          WITH L_BUKRS L_WA_MSGV SPACE SPACE.
* 006(MOD)↑------------------------------------------------
*     バックグラウンド実行の場合
      ELSE.
        L_WA_MSGV = L_C_ACTVT.
        MESSAGE ID 'ZPNM001' TYPE C_MSGTY-SUCCESS NUMBER '638'
* 006(MOD)↓------------------------------------------------
*          WITH L_BUKRS L_WA_MSGV  ##MG_MISSING
          WITH L_BUKRS L_WA_MSGV SPACE SPACE
* 006(MOD)↑------------------------------------------------
          DISPLAY LIKE C_MSGTY-ERROR.
        LEAVE PROGRAM.
      ENDIF.

*      CONCATENATE 'プラント=' P_WERKS INTO L_WA_MSGV.
*      MESSAGE ID 'ZPNM001' TYPE C_MSGTY-ERROR NUMBER '638'
*        WITH L_BUKRS L_WA_MSGV  ##MG_MISSING.
* 004(MOD)↑------------------------------------------------
    ENDIF.
  ENDIF.

ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_EDIT_MESSAGE
*&---------------------------------------------------------------------*
*& メッセージ設定
*&---------------------------------------------------------------------*
*&      --> C_MSGTY_ERROR
*&      --> P_
*&      --> L_MSGNO
*&      --> V_WK_ERRMSG     メッセージテキスト
*&      --> L_WA_MSGV
*&      <-- IT_RETURN
*&---------------------------------------------------------------------*
FORM FM_EDIT_MESSAGE
  USING    V_MSGTY     TYPE MSGTY
           V_MSGID     TYPE MSGID
* 002(MOD)↓------------------------------------------------
*           V_MSGNO     TYPE MSGNO
           V_MSGNO     TYPE MSGNO_EXT
           V_WK_ERRMSG TYPE MSGTXT_LONG
* 002(MOD)↑------------------------------------------------
           V_WA_MSGV   TYPE TA_MSGV
  CHANGING V_IT_RETURN TYPE ZDCD_ERRIFOP_ST01.

* WA
  DATA L_WA_RETURN TYPE ZDCD_ERRIFOP_S01.

  L_WA_RETURN-MSGTY = V_MSGTY.
  L_WA_RETURN-MSGID = V_MSGID.
  L_WA_RETURN-MSGNO = V_MSGNO.
  L_WA_RETURN-MSGV1 = V_WA_MSGV-MSGV1.
  L_WA_RETURN-MSGV2 = V_WA_MSGV-MSGV2.
  L_WA_RETURN-MSGV3 = V_WA_MSGV-MSGV3.
  L_WA_RETURN-MSGV4 = V_WA_MSGV-MSGV4.
* 002(ADD)↓------------------------------------------------
  L_WA_RETURN-ERRMSG = V_WK_ERRMSG.       "メッセージテキスト
* 002(ADD)↑------------------------------------------------

* 002(DEL)↓------------------------------------------------
*  MESSAGE ID V_MSGID TYPE V_MSGTY NUMBER V_MSGNO
*    WITH V_WA_MSGV-MSGV1 V_WA_MSGV-MSGV2 V_WA_MSGV-MSGV3 V_WA_MSGV-MSGV4
*    INTO L_WA_RETURN-ERRMSG.
* 002(DEL)↓------------------------------------------------

  APPEND L_WA_RETURN TO V_IT_RETURN.

ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_GET_COMMON_PARM
*&---------------------------------------------------------------------*
*& 共通パラメータ取得
*&---------------------------------------------------------------------*
*& -->  p1        text
*& <--  p2        text
*&---------------------------------------------------------------------*
FORM FM_GET_COMMON_PARM .

* 共通パラメータ：BPグルーピング
  CALL FUNCTION 'Z_DCD_COMMON_PARAMS'
    EXPORTING
      I_PROGRAM_ID       = SY-CPROG
      I_PARAM_ID         = C_PARAMID-BP_GROUP
    IMPORTING
      E_VALUE            = WK_BU_GROUP
    EXCEPTIONS
      INVALID_PROGRAM_ID = 1
      INVALID_PARAM_ID   = 2
      DATA_NOT_FOUND     = 3
      DATA_TYPES_ERROR   = 4
      OTHERS             = 9.
  IF SY-SUBRC <> 0.
* 002(MOD)↓------------------------------------------------
*    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-ABORT NUMBER '602'
    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-ERROR NUMBER '602'
* 002(MOD)↑------------------------------------------------
* 006(MOD)↓------------------------------------------------
*      WITH C_PARAMID-BP_GROUP  ##MG_MISSING.
      WITH C_PARAMID-BP_GROUP SPACE SPACE SPACE.
* 006(MOD)↑------------------------------------------------
  ENDIF.

* 共通パラメータ：権限オブジェクト
  CALL FUNCTION 'Z_DCD_COMMON_PARAMS'
    EXPORTING
      I_PROGRAM_ID       = SY-CPROG
      I_PARAM_ID         = C_PARAMID-OBJCT
    IMPORTING
      E_VALUE            = WK_OBJCT
    EXCEPTIONS
      INVALID_PROGRAM_ID = 1
      INVALID_PARAM_ID   = 2
      DATA_NOT_FOUND     = 3
      DATA_TYPES_ERROR   = 4
      OTHERS             = 9.
  IF SY-SUBRC <> 0.
* 002(MOD)↓------------------------------------------------
*    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-ABORT NUMBER '602'
    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-ERROR NUMBER '602'
* 002(MOD)↑------------------------------------------------
* 006(MOD)↓------------------------------------------------
*      WITH C_PARAMID-OBJCT  ##MG_MISSING.
      WITH C_PARAMID-OBJCT SPACE SPACE SPACE.
* 006(MOD)↑------------------------------------------------
  ENDIF.

ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_GET_SYSTEM_DATA
*&---------------------------------------------------------------------*
*& システムデータ取得
*&---------------------------------------------------------------------*
*& -->  p1        text
*& <--  p2        text
*&---------------------------------------------------------------------*
FORM FM_GET_SYSTEM_DATA .

  CALL FUNCTION 'Z_DCD_EDIT_SYSDATA'
    CHANGING
      C_SYSDATA = WA_SYSDATA.

ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_INITIAL_PROC
*&---------------------------------------------------------------------*
*& 初期化処理
*&---------------------------------------------------------------------*
*& -->  p1        text
*& <--  p2        text
*&---------------------------------------------------------------------*
FORM FM_INITIAL_PROC .

*選択画面ラベルテキスト設定
*共通Includeで事前定義済サブルーチンを呼び出す
  PERFORM FM_SET_LBLTEXT.

* 003(DEL)↓------------------------------------------------
** システムデータ取得
*  PERFORM FM_GET_SYSTEM_DATA.
* 003(DEL)↑------------------------------------------------

* 共通パラメータ取得
  PERFORM FM_GET_COMMON_PARM.

ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_INPUT_CHECK_KUNNR
*&---------------------------------------------------------------------*
*& 入力チェック(得意先（送信先）)
*&---------------------------------------------------------------------*
*& -->  p1        text
*& <--  p2        text
*&---------------------------------------------------------------------*
FORM FM_INPUT_CHECK_KUNNR .

* WK
  DATA L_PARTNER TYPE BU_PARTNER  ##NEEDED.
  DATA L_MSGV    TYPE MSGV_EXT.

  SELECT SINGLE PARTNER INTO @L_PARTNER
    FROM BUT000
    WHERE PARTNER  = @P_KUNNR
      AND BU_GROUP = @WK_BU_GROUP.
  IF SY-SUBRC <> 0.
* 006(MOD)↓------------------------------------------------
*    CONCATENATE 'BPグルーピング=' WK_BU_GROUP INTO L_MSGV.
*    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-ERROR NUMBER '612'
*      WITH '得意先（送信先）' P_KUNNR L_MSGV ##MG_MISSING.
    CONCATENATE TEXT-001 WK_BU_GROUP INTO L_MSGV.
    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-ERROR NUMBER '612'
      WITH TEXT-002 P_KUNNR L_MSGV SPACE.
* 006(MOD)↑------------------------------------------------
  ENDIF.

ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_INPUT_CHECK_WERKS
*&---------------------------------------------------------------------*
*& 入力チェック(プラント)
*&---------------------------------------------------------------------*
*& -->  p1        text
*& <--  p2        text
*&---------------------------------------------------------------------*
FORM FM_INPUT_CHECK_WERKS .

* WK
  DATA L_WERKS TYPE WERKS_D  ##NEEDED.

  SELECT SINGLE WERKS INTO @L_WERKS
    FROM T001W
    WHERE T001W~WERKS = @P_WERKS.
  IF SY-SUBRC <> 0.
    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-ERROR NUMBER '612'
* 006(MOD)↓------------------------------------------------
*      WITH 'プラント' P_WERKS  ##MG_MISSING.
      WITH TEXT-003 P_WERKS SPACE SPACE.
* 006(MOD)↑------------------------------------------------
  ENDIF.

ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_INSERT_ZPNM036
*&---------------------------------------------------------------------*
*& 履歴テーブル登録
*&---------------------------------------------------------------------*
*&      --> IT_OUTPUTDATA
*&      <-- L_ERRFLG
*&---------------------------------------------------------------------*
FORM FM_INSERT_ZPNM036
  USING    V_IT_OUTPUTDATA TYPE ZPNM_OUT_SM2CR001_ST01
  CHANGING V_ERRFLG        TYPE FLAG.

* IT
  DATA L_IT_OUTPUTDATA_INSKEY TYPE ZPNM_OUT_SM2CR001_ST01.
  DATA L_IT_ZPNM036           TYPE STANDARD TABLE OF ZPNM036.

* WA
  DATA L_WA_ZPNM036 TYPE ZPNM036.
  DATA L_WA_MSGV    TYPE TA_MSGV.

* WK
  DATA L_MSGTY TYPE MSGTY.
* 002(MOD)↓------------------------------------------------
*  DATA L_MSGNO TYPE MSGNO.
  DATA L_WK_ERRMSG TYPE MSGTXT_LONG.    "メッセージテキスト
* 002(MOD)↑------------------------------------------------

* FS
  FIELD-SYMBOLS <FS_OUTPUTDATA> TYPE ZPNM_OUT_SM2CR001_S01.

  L_IT_OUTPUTDATA_INSKEY = V_IT_OUTPUTDATA.
* 001(MOD)↓------------------------------------------------
*  SORT L_IT_OUTPUTDATA_INSKEY BY KUNNR IDETF.
  SORT L_IT_OUTPUTDATA_INSKEY
   ASCENDING BY KUNNR                                 "得意先（送信先）
                WERKS                                 "プラント
                IDETF                                 "個体識別番号
                ZZWERKS                               "一般ブランド
                MATNR.                                "品目コード
* 001(MOD)↑------------------------------------------------
  DELETE ADJACENT DUPLICATES FROM L_IT_OUTPUTDATA_INSKEY
* 001(MOD)↓------------------------------------------------
*    COMPARING KUNNR IDETF.
    COMPARING KUNNR                                   "得意先（送信先）
              WERKS                                   "プラント
              IDETF                                   "個体識別番号
              ZZWERKS                                 "一般ブランド
              MATNR.                                  "品目コード
* 001(MOD)↑------------------------------------------------

  L_WA_ZPNM036-CREDATE = WA_SYSDATA-CREDATE.
  L_WA_ZPNM036-CRETIME = WA_SYSDATA-CRETIME.
  L_WA_ZPNM036-CREUSER = WA_SYSDATA-CREUSER.
  L_WA_ZPNM036-CREPROG = WA_SYSDATA-CREPROG.
  L_WA_ZPNM036-CRETRAN = WA_SYSDATA-CRETRAN.

  LOOP AT L_IT_OUTPUTDATA_INSKEY ASSIGNING <FS_OUTPUTDATA>.
    L_WA_ZPNM036-KUNNR = <FS_OUTPUTDATA>-KUNNR.
* 001(ADD)↓------------------------------------------------
    L_WA_ZPNM036-WERKS = <FS_OUTPUTDATA>-WERKS.       "プラント
* 001(ADD)↑------------------------------------------------
    L_WA_ZPNM036-IDETF = <FS_OUTPUTDATA>-IDETF.
* 001(ADD)↓------------------------------------------------
    L_WA_ZPNM036-ZZWERKS = <FS_OUTPUTDATA>-ZZWERKS.   "一般ブランド
    L_WA_ZPNM036-MATNR   = <FS_OUTPUTDATA>-MATNR.     "品目コード
* 001(ADD)↑------------------------------------------------

    APPEND L_WA_ZPNM036 TO L_IT_ZPNM036.
  ENDLOOP.

  INSERT ZPNM036 FROM TABLE L_IT_ZPNM036 ACCEPTING DUPLICATE KEYS.

  IF SY-SUBRC <> 0 AND SY-SUBRC <> 4.
    ROLLBACK WORK.

    L_MSGTY = C_MSGTY-ERROR.
* 001(DEL)↓------------------------------------------------
*    L_MSGNO = '607'.
* 001(DEL)↑------------------------------------------------
    L_WA_MSGV-MSGV1 = 'ZPNM036/INSERT'.
    L_WA_MSGV-MSGV2 = SY-SUBRC.
    CONDENSE L_WA_MSGV-MSGV2.
    L_WA_MSGV-MSGV3 = SY-DBCNT.
    CONDENSE L_WA_MSGV-MSGV3.
    L_WA_MSGV-MSGV4 = ''.
* 002(ADD)↓------------------------------------------------
    MESSAGE ID 'ZPNM001' TYPE L_MSGTY NUMBER '607'
      WITH L_WA_MSGV-MSGV1 L_WA_MSGV-MSGV2 L_WA_MSGV-MSGV3 L_WA_MSGV-MSGV4
      INTO L_WK_ERRMSG.
* 002(ADD)↑------------------------------------------------
    PERFORM FM_EDIT_MESSAGE
      USING    L_MSGTY
* 002(MOD)↓------------------------------------------------
*               'ZPNM001'
*               L_MSGNO
               SY-MSGID
               SY-MSGNO
               L_WK_ERRMSG
* 002(MOD)↑------------------------------------------------
               L_WA_MSGV
      CHANGING IT_RETURN.

* 002(MOD)↓------------------------------------------------
*    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-SUCCESS NUMBER L_MSGNO
    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-SUCCESS NUMBER '607'
* 002(MOD)↑------------------------------------------------
      WITH L_WA_MSGV-MSGV1 L_WA_MSGV-MSGV2 L_WA_MSGV-MSGV3 L_WA_MSGV-MSGV4
      DISPLAY LIKE L_MSGTY.

    V_ERRFLG = 'X'.
  ENDIF.

  FREE L_IT_OUTPUTDATA_INSKEY.
  FREE L_IT_ZPNM036.

ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_MAIN_PROC
*&---------------------------------------------------------------------*
*& 主処理
*&---------------------------------------------------------------------*
*& -->  p1        text
*& <--  p2        text
*&---------------------------------------------------------------------*
FORM FM_MAIN_PROC .

* WA
  DATA L_WA_DATANUM TYPE ZDCD_DATANUM_S01.
  DATA L_WA_MSGV    TYPE TA_MSGV.

* WK
  DATA L_MSGTY  TYPE MSGTY.
* 002(MOD)↓------------------------------------------------
*  DATA L_MSGNO  TYPE MSGNO.
  DATA L_WK_ERRMSG TYPE MSGTXT_LONG.    "メッセージテキスト
* 002(MOD)↑------------------------------------------------
  DATA L_ERRFLG TYPE FLAG.

* 共通モジュール用
  DATA L_GUID        TYPE ZDCDEGUID.
  DATA L_OP_FPATH    TYPE ZDCDEFILEPATH.
  DATA L_NO_ITM_PROC TYPE INT4.
  DATA L_NO_SUCCESS  TYPE INT4.
  DATA L_NO_FAILURE  TYPE INT4.

* 003(ADD)↓------------------------------------------------
* システムデータ取得
  PERFORM FM_GET_SYSTEM_DATA.
* 003(ADD)↑------------------------------------------------
* 処理開始メッセージ
  MESSAGE ID 'ZPNM001' TYPE C_MSGTY-SUCCESS NUMBER '641'
* 006(MOD)↓------------------------------------------------
*    WITH P_KUNNR  ##MG_MISSING.
    WITH P_KUNNR SPACE SPACE SPACE.
* 006(MOD)↑------------------------------------------------

* 初期処理
* 共通Includeで事前定義済サブルーチンを呼び出す
  PERFORM FM_COMMON_INT.

* 排他開始
  CALL FUNCTION 'ENQUEUE_EZZZPNM036_1'
    EXPORTING
      MANDT = SY-MANDT
      KUNNR = P_KUNNR
    EXCEPTIONS
      FOREIGN_LOCK   = 1
      SYSTEM_FAILURE = 2
      OTHERS         = 9.
  IF SY-SUBRC <> 0.
    MESSAGE ID SY-MSGID TYPE C_MSGTY-SUCCESS NUMBER SY-MSGNO
      WITH SY-MSGV1 SY-MSGV2 SY-MSGV3 SY-MSGV4
      DISPLAY LIKE SY-MSGTY.

    L_MSGTY = C_MSGTY-ERROR.
* 002(DEL)↓------------------------------------------------
*    L_MSGNO = '643'.
* 002(DEL)↑------------------------------------------------
    L_WA_MSGV-MSGV1 = P_KUNNR.
    L_WA_MSGV-MSGV2 = ''.
    L_WA_MSGV-MSGV3 = ''.
    L_WA_MSGV-MSGV4 = ''.
* 002(ADD)↓------------------------------------------------
    MESSAGE ID 'ZPNM001' TYPE L_MSGTY NUMBER '643'
      WITH L_WA_MSGV-MSGV1 L_WA_MSGV-MSGV2 L_WA_MSGV-MSGV3 L_WA_MSGV-MSGV4
      INTO L_WK_ERRMSG.
* 002(ADD)↑------------------------------------------------
    PERFORM FM_EDIT_MESSAGE
      USING    L_MSGTY
* 002(MOD)↓------------------------------------------------
*               'ZPNM001'
*               L_MSGNO
               SY-MSGID
               SY-MSGNO
               L_WK_ERRMSG
* 002(MOD)↑------------------------------------------------
               L_WA_MSGV
      CHANGING IT_RETURN.

* 002(MOD)↓------------------------------------------------
*    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-SUCCESS NUMBER L_MSGNO
    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-SUCCESS NUMBER '643'
* 002(MOD)↑------------------------------------------------
      WITH L_WA_MSGV-MSGV1 L_WA_MSGV-MSGV2 L_WA_MSGV-MSGV3 L_WA_MSGV-MSGV4
      DISPLAY LIKE L_MSGTY.

*   FM_COMMON_MAIN - FM_OUTPUT_LOG
    PERFORM FM_OUTPUT_LOG_Z053
      USING    L_GUID
      CHANGING IT_RETURN.

*   FM_COMMON_MAIN - FM_ALV_DISPLAY
    PERFORM FM_ALV_DISPLAY_Z053
      USING L_GUID
            L_OP_FPATH
            L_NO_ITM_PROC
            L_NO_SUCCESS
            L_NO_FAILURE
            IT_RETURN.
    RETURN.
  ENDIF.

* データ取得
  CALL FUNCTION 'Z_PNM_OUT_SM2CR001'
    EXPORTING
      I_KUNNR    = P_KUNNR
      I_WERKS    = P_WERKS
      IT_S_LGORT = S_LGORT[]
      IT_S_MATNR = S_MATNR[]
      IT_S_BUDAT = S_BUDAT[]
      IT_S_LIFNR = S_LIFNR[]
      IT_S_IDETF = S_IDETF[]
      IT_S_CHARG = S_CHARG[]
      I_RCVR     = CB_RCVR
    IMPORTING
      ET_RETURN     = IT_RETURN
      ET_OUTPUTDATA = IT_OUTPUTDATA
      ES_DATANUM    = L_WA_DATANUM.

  IF L_WA_DATANUM-NUM_SUCCESS <> 0.
*   履歴テーブル登録
    PERFORM FM_INSERT_ZPNM036
      USING    IT_OUTPUTDATA
      CHANGING L_ERRFLG.
  ELSE.
    L_MSGTY = C_MSGTY-SUCCESS.
* 002(DEL)↓------------------------------------------------
*    L_MSGNO = '646'.
* 002(DEL)↑------------------------------------------------
    L_WA_MSGV-MSGV1 = P_KUNNR.
    L_WA_MSGV-MSGV2 = ''.
    L_WA_MSGV-MSGV3 = ''.
    L_WA_MSGV-MSGV4 = ''.
* 002(ADD)↓------------------------------------------------
    MESSAGE ID 'ZPNM001' TYPE L_MSGTY NUMBER '646'
      WITH L_WA_MSGV-MSGV1 L_WA_MSGV-MSGV2 L_WA_MSGV-MSGV3 L_WA_MSGV-MSGV4
      INTO L_WK_ERRMSG.
* 002(ADD)↑------------------------------------------------
    PERFORM FM_EDIT_MESSAGE
      USING    L_MSGTY
* 002(MOD)↓------------------------------------------------
*               'ZPNM001'
*               L_MSGNO
               SY-MSGID
               SY-MSGNO
               L_WK_ERRMSG
* 002(MOD)↑------------------------------------------------
               L_WA_MSGV
      CHANGING IT_RETURN.

* 002(MOD)↓------------------------------------------------
*    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-SUCCESS NUMBER L_MSGNO
    MESSAGE ID 'ZPNM001' TYPE C_MSGTY-SUCCESS NUMBER '646'
* 002(MOD)↑------------------------------------------------
      WITH L_WA_MSGV-MSGV1 L_WA_MSGV-MSGV2 L_WA_MSGV-MSGV3 L_WA_MSGV-MSGV4
      DISPLAY LIKE L_MSGTY.

     L_ERRFLG = 'X'.

  ENDIF.

  IF L_ERRFLG IS INITIAL .
*   配信Include側処理
*   検索データ設定
    PERFORM FM_SRCH_DATA_SET
      CHANGING IT_SRCH_KEY_INFO.

*   コミットフラグ
    FLG_COMMIT_SYNC = ABAP_ON.

**   出力処理
**   共通Includeで事前定義済サブルーチンを呼び出す
*    PERFORM FM_COMMON_MAIN
*      USING IT_OUTPUTDATA
*            IT_SRCH_KEY_INFO
*            IT_RETURN
*            L_WA_DATANUM.

*   FM_COMMON_MAIN - FM_OUTPUT_DATA
    PERFORM FM_OUTPUT_DATA_Z053
      USING    IT_OUTPUTDATA
               IT_SRCH_KEY_INFO
               L_WA_DATANUM
      CHANGING L_GUID
               L_OP_FPATH
               L_NO_ITM_PROC
               L_NO_SUCCESS
               L_NO_FAILURE
               IT_RETURN.
  ENDIF.

* 排他終了
  CALL FUNCTION 'DEQUEUE_EZZZPNM036_1'
    EXPORTING
      MANDT = SY-MANDT
      KUNNR = P_KUNNR.

  CLEAR L_WA_MSGV.
* 002(ADD)↓------------------------------------------------
* 処理が終了しました &1 &2 &3 &4
  MESSAGE S647(ZPNM001)
    WITH L_WA_MSGV-MSGV1 L_WA_MSGV-MSGV2 L_WA_MSGV-MSGV3 L_WA_MSGV-MSGV4
    INTO L_WK_ERRMSG.
* 002(ADD)↑------------------------------------------------
  PERFORM FM_EDIT_MESSAGE
    USING    C_MSGTY-SUCCESS
* 002(MOD)↓------------------------------------------------
*             'ZPNM001'
*             '647'
             SY-MSGID
             SY-MSGNO
             L_WK_ERRMSG
* 002(MOD)↑------------------------------------------------
             L_WA_MSGV
    CHANGING IT_RETURN.

* FM_COMMON_MAIN - FM_OUTPUT_LOG
  PERFORM FM_OUTPUT_LOG_Z053
    USING    L_GUID
    CHANGING IT_RETURN.

* 処理終了メッセージ
  MESSAGE ID 'ZPNM001' TYPE C_MSGTY-SUCCESS NUMBER '642'
* 006(MOD)↓------------------------------------------------
*    WITH P_KUNNR  ##MG_MISSING.
    WITH P_KUNNR SPACE SPACE SPACE.
* 006(MOD)↑------------------------------------------------


* FM_COMMON_MAIN - FM_ALV_DISPLAY
  PERFORM FM_ALV_DISPLAY_Z053
    USING L_GUID
          L_OP_FPATH
          L_NO_ITM_PROC
          L_NO_SUCCESS
          L_NO_FAILURE
          IT_RETURN.


ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_OUTPUT_DATA_Z053
*&---------------------------------------------------------------------*
*& FM_COMMON_MAIN - FM_OUTPUT_DATA
*&---------------------------------------------------------------------*
*&      --> IT_OUTPUTDATA
*&      --> IT_SRCH_KEY_INFO
*&      --> L_WA_DATANUM
*&      <-- L_WK_GUID
*&      <-- L_WK_OP_FPATH
*&      <-- L_WK_NO_ITM_PROC
*&      <-- L_WK_NO_SUCCESS
*&      <-- L_WK_NO_FAILURE
*&      <-- IT_RETURN
*&---------------------------------------------------------------------*
FORM FM_OUTPUT_DATA_Z053
  USING    V_IT_OUTPUTDATA    TYPE ZPNM_OUT_SM2CR001_ST01
           V_IT_SRCH_KEY_INFO TYPE TAT_SRCH_KEY_INFO
           V_WA_DATANUM       TYPE ZDCD_DATANUM_S01
  CHANGING V_GUID             TYPE ZDCDEGUID
           V_OP_FPATH         TYPE ZDCDEFILEPATH
           V_NO_ITM_PROC      TYPE INT4
           V_NO_SUCCESS       TYPE INT4
           V_NO_FAILURE       TYPE INT4
           V_IT_RETURN        TYPE ZDCD_ERRIFOP_ST01.

  PERFORM FM_OUTPUT_DATA
    USING    V_IT_OUTPUTDATA
             V_IT_SRCH_KEY_INFO
             V_WA_DATANUM
    CHANGING V_GUID
             V_OP_FPATH
             V_NO_ITM_PROC
             V_NO_SUCCESS
             V_NO_FAILURE
             V_IT_RETURN.

ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_OUTPUT_LOG_Z053
*&---------------------------------------------------------------------*
*& FM_COMMON_MAIN - FM_OUTPUT_LOG
*&---------------------------------------------------------------------*
*&      --> L_WK_GUID
*&      <-- IT_RETURN
*&---------------------------------------------------------------------*
FORM FM_OUTPUT_LOG_Z053
  USING    V_GUID      TYPE ZDCDEGUID
  CHANGING V_IT_RETURN TYPE ZDCD_ERRIFOP_ST01.

  PERFORM FM_OUTPUT_LOG
    USING    V_GUID
    CHANGING V_IT_RETURN.

ENDFORM.
*&---------------------------------------------------------------------*
*& Form FM_SRCH_DATA_SET
*&---------------------------------------------------------------------*
*& 検索データ設定
*&---------------------------------------------------------------------*
*&      <-- IT_SRCH_KEY_INFO
*&---------------------------------------------------------------------*
FORM FM_SRCH_DATA_SET
  CHANGING V_IT_SRCH_KEY_INFO TYPE TAT_SRCH_KEY_INFO.

  DATA L_WA_SRCH_KEY TYPE ZDCD_SERCHKEY_S01.

  DATA L_WA_S_LGORT LIKE LINE OF S_LGORT.
  DATA L_WA_S_MATNR LIKE LINE OF S_MATNR.
  DATA L_WA_S_BUDAT LIKE LINE OF S_BUDAT.
  DATA L_WA_S_LIFNR LIKE LINE OF S_LIFNR.
  DATA L_WA_S_IDETF LIKE LINE OF S_IDETF.
  DATA L_WA_S_CHARG LIKE LINE OF S_CHARG.

* 得意先（送信先）
  IF P_KUNNR IS NOT INITIAL.
    L_WA_SRCH_KEY-SIGN    =  'I'.
    L_WA_SRCH_KEY-OPTION  =  'EQ'.
    L_WA_SRCH_KEY-LOW     =  P_KUNNR.
    L_WA_SRCH_KEY-HIGH    =  ''.
    L_WA_SRCH_KEY-PARAMID =  C_PARA_ID-KUNNR.
    APPEND L_WA_SRCH_KEY TO V_IT_SRCH_KEY_INFO.
  ENDIF.

* プラント
  IF P_WERKS IS NOT INITIAL.
    L_WA_SRCH_KEY-SIGN    =  'I'.
    L_WA_SRCH_KEY-OPTION  =  'EQ'.
    L_WA_SRCH_KEY-LOW     =  P_WERKS.
    L_WA_SRCH_KEY-HIGH    =  ''.
    L_WA_SRCH_KEY-PARAMID =  C_PARA_ID-WERKS.
    APPEND L_WA_SRCH_KEY TO V_IT_SRCH_KEY_INFO.
  ENDIF.

* 保管場所
  LOOP AT S_LGORT INTO L_WA_S_LGORT.
    L_WA_SRCH_KEY-SIGN    =  L_WA_S_LGORT-SIGN.
    L_WA_SRCH_KEY-OPTION  =  L_WA_S_LGORT-OPTION.
    L_WA_SRCH_KEY-LOW     =  L_WA_S_LGORT-LOW.
    L_WA_SRCH_KEY-HIGH    =  L_WA_S_LGORT-HIGH.
    L_WA_SRCH_KEY-PARAMID =  C_PARA_ID-LGORT.
    APPEND L_WA_SRCH_KEY TO V_IT_SRCH_KEY_INFO.
  ENDLOOP.

* 品目
  LOOP AT S_MATNR INTO L_WA_S_MATNR.
    L_WA_SRCH_KEY-SIGN    =  L_WA_S_MATNR-SIGN.
    L_WA_SRCH_KEY-OPTION  =  L_WA_S_MATNR-OPTION.
    L_WA_SRCH_KEY-LOW     =  L_WA_S_MATNR-LOW.
    L_WA_SRCH_KEY-HIGH    =  L_WA_S_MATNR-HIGH.
    L_WA_SRCH_KEY-PARAMID =  C_PARA_ID-MATNR.
    APPEND L_WA_SRCH_KEY TO V_IT_SRCH_KEY_INFO.
  ENDLOOP.

* 転記日付
  LOOP AT S_BUDAT INTO L_WA_S_BUDAT.
    L_WA_SRCH_KEY-SIGN    =  L_WA_S_BUDAT-SIGN.
    L_WA_SRCH_KEY-OPTION  =  L_WA_S_BUDAT-OPTION.
    L_WA_SRCH_KEY-LOW     =  L_WA_S_BUDAT-LOW.
    L_WA_SRCH_KEY-HIGH    =  L_WA_S_BUDAT-HIGH.
    L_WA_SRCH_KEY-PARAMID =  C_PARA_ID-BUDAT.
    APPEND L_WA_SRCH_KEY TO V_IT_SRCH_KEY_INFO.
  ENDLOOP.

* 仕入先
  LOOP AT S_LIFNR INTO L_WA_S_LIFNR.
    L_WA_SRCH_KEY-SIGN    =  L_WA_S_LIFNR-SIGN.
    L_WA_SRCH_KEY-OPTION  =  L_WA_S_LIFNR-OPTION.
    L_WA_SRCH_KEY-LOW     =  L_WA_S_LIFNR-LOW.
    L_WA_SRCH_KEY-HIGH    =  L_WA_S_LIFNR-HIGH.
    L_WA_SRCH_KEY-PARAMID =  C_PARA_ID-LIFNR.
    APPEND L_WA_SRCH_KEY TO V_IT_SRCH_KEY_INFO.
  ENDLOOP.

* 個体識別番号
  LOOP AT S_IDETF INTO L_WA_S_IDETF.
    L_WA_SRCH_KEY-SIGN    =  L_WA_S_IDETF-SIGN.
    L_WA_SRCH_KEY-OPTION  =  L_WA_S_IDETF-OPTION.
    L_WA_SRCH_KEY-LOW     =  L_WA_S_IDETF-LOW.
    L_WA_SRCH_KEY-HIGH    =  L_WA_S_IDETF-HIGH.
    L_WA_SRCH_KEY-PARAMID =  C_PARA_ID-IDETF.
    APPEND L_WA_SRCH_KEY TO V_IT_SRCH_KEY_INFO.
  ENDLOOP.

* ロット番号
  LOOP AT S_CHARG INTO L_WA_S_CHARG.
    L_WA_SRCH_KEY-SIGN    =  L_WA_S_CHARG-SIGN.
    L_WA_SRCH_KEY-OPTION  =  L_WA_S_CHARG-OPTION.
    L_WA_SRCH_KEY-LOW     =  L_WA_S_CHARG-LOW.
    L_WA_SRCH_KEY-HIGH    =  L_WA_S_CHARG-HIGH.
    L_WA_SRCH_KEY-PARAMID =  C_PARA_ID-CHARG.
    APPEND L_WA_SRCH_KEY TO V_IT_SRCH_KEY_INFO.
  ENDLOOP.

* リカバリ実行
  IF CB_RCVR IS NOT INITIAL.
    L_WA_SRCH_KEY-SIGN    =  'I'.
    L_WA_SRCH_KEY-OPTION  =  'EQ'.
    L_WA_SRCH_KEY-LOW     =  CB_RCVR.
    L_WA_SRCH_KEY-HIGH    =  ''.
    L_WA_SRCH_KEY-PARAMID =  C_PARA_ID-RCVR.
    APPEND L_WA_SRCH_KEY TO V_IT_SRCH_KEY_INFO.
  ENDIF.

ENDFORM.
*
