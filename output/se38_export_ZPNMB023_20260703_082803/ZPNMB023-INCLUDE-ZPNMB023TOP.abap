*&---------------------------------------------------------------------*
*& Include ZPNMB023TOP                              - Report ZPNMB023
*&---------------------------------------------------------------------*
*-----------------------------------------------------------------------
* 型定義
*-----------------------------------------------------------------------
TYPES TAT_SRCH_KEY_INFO TYPE STANDARD TABLE OF ZDCD_SERCHKEY_S01.          "検索キー情報
*
TYPES:
  BEGIN OF TA_MSGV,
    MSGV1 TYPE MSGV1,  "
    MSGV2 TYPE MSGV2,  "
    MSGV3 TYPE MSGV3,  "
    MSGV4 TYPE MSGV4,  "
  END OF TA_MSGV.
*
*----------------------------------------------------------------------*
* 内部テーブル宣言.
*----------------------------------------------------------------------*
DATA IT_SRCH_KEY_INFO TYPE TAT_SRCH_KEY_INFO  ##NEEDED.       "内部TBL: 検索キー情報
DATA IT_RETURN        TYPE ZDCD_ERRIFOP_ST01  ##NEEDED.       "内部TBL: リターンメッセージ
DATA IT_OUTPUTDATA    TYPE ZPNM_OUT_SM2CR001_ST01  ##NEEDED.  "
*
*-----------------------------------------------------------------------
* 変数宣言
*-----------------------------------------------------------------------
* システムデータ取得用
DATA WA_SYSDATA  TYPE ZDCD_SYSDATA_S01  ##NEEDED.
* 共通パラメータ取得用
DATA WK_BU_GROUP TYPE BU_GROUP  ##NEEDED.
DATA WK_OBJCT TYPE XUOBJECT  ##NEEDED.
* 画面項目
DATA WK_LGORT TYPE T001L-LGORT.
DATA WK_MATNR TYPE MATNR.
DATA WK_BUDAT TYPE BUDAT.
DATA WK_LIFNR TYPE LIFNR.
DATA WK_IDETF TYPE ZPNMEIDETFH.
DATA WK_CHARG TYPE MCHB-CHARG.
*
*-----------------------------------------------------------------------
* 定数定義
*-----------------------------------------------------------------------
* 共通パラメータ関連
CONSTANTS:
  BEGIN OF C_PARAMID,
    BP_GROUP TYPE ZDCDECMPID VALUE 'BP_GROUP',  "BPグループイング
    OBJCT    TYPE ZDCDECMPID VALUE 'OBJCT',     "権限オブジェクト
  END OF C_PARAMID.
* PARA_ID
CONSTANTS:
  BEGIN OF C_PARA_ID,
    KUNNR(9) TYPE C VALUE 'IT_KUNNR',
    WERKS(9) TYPE C VALUE 'IT_WERKS',
    LGORT(9) TYPE C VALUE 'IT_LGORT',
    MATNR(9) TYPE C VALUE 'IT_MATNR',
    BUDAT(9) TYPE C VALUE 'IT_BUDAT',
    LIFNR(9) TYPE C VALUE 'IT_LIFNR',
    IDETF(9) TYPE C VALUE 'IT_IDETF',
    CHARG(9) TYPE C VALUE 'IT_CHARG',
    RCVR(9)  TYPE C VALUE 'CB_RCVR',
  END OF C_PARA_ID.
* MSGTY
CONSTANTS:
  BEGIN OF C_MSGTY,
    SUCCESS TYPE MSGTY VALUE 'S',  "
    WARNING TYPE MSGTY VALUE 'W',  "
    ERROR   TYPE MSGTY VALUE 'E',  "
    ABORT   TYPE MSGTY VALUE 'A',  "
  END OF C_MSGTY.
*
*----------------------------------------------------------------------*
*選択画面定義
*----------------------------------------------------------------------*
PARAMETERS     P_KUNNR TYPE ZPNMEKUNNR  OBLIGATORY.
PARAMETERS     P_WERKS TYPE T001L-WERKS OBLIGATORY.
SELECT-OPTIONS S_LGORT FOR  WK_LGORT    OBLIGATORY.
SELECT-OPTIONS S_MATNR FOR  WK_MATNR    OBLIGATORY.
SELECT-OPTIONS S_BUDAT FOR  WK_BUDAT    OBLIGATORY NO-EXTENSION.
SELECT-OPTIONS S_LIFNR FOR  WK_LIFNR.
SELECT-OPTIONS S_IDETF FOR  WK_IDETF    NO INTERVALS.
SELECT-OPTIONS S_CHARG FOR  WK_CHARG    NO INTERVALS.

SELECTION-SCREEN SKIP 1.

PARAMETERS     CB_RCVR AS CHECKBOX.

SELECTION-SCREEN SKIP 1.
*
