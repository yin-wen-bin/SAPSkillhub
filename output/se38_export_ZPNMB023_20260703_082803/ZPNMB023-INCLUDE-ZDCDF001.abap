*----------------------------------------------------------------------*
* Program ID  ： ZDCDF001
* Program Name： 配信型レポート用Include
*
* Program Overview： 本機能は各業務要件で作成する送信IFレポートプログラムのEAI送信デー
*                   タ登録機能を共通化し提供するものである。
*
* Created On：2021/01/13            Created by： Uday Teegala
* Coding standard Doc:V2.00
* Development Version:SAP S/4HANA
* Terms of use：Possible to use only SAP S/4HANA
*----------------------------------------------------------------------*
*  Copyright(C) FUJITSU LIMITED
*  All Rights Reserved.
*----------------------------------------------------------------------*
*&---------------------------------------------------------------------*
*& Include ZDCDF001
*&---------------------------------------------------------------------*
*----------------------------------------------------------------------*
* Change Number：001
* Updated On：2021/04/29           Updated By： Uday Teegala
* Change Content：Control No.(Change No.CR-10)
* CR-10: Change file name type from STRING type to CHAR type
*----------------------------------------------------------------------*
*----------------------------------------------------------------------*
* Change Number：002
* Updated On：2021/06/23           Updated By： Uday Teegala
* Change Content：Control No.(Change No.IT-0017)
* IT-0017:  Change in out process without considering whether the output
*           target data has a record or not
*----------------------------------------------------------------------*
*----------------------------------------------------------------------*
* Change Number：003
* Updated On：2021/06/28           Updated By： Uday Teegala
* Change Content：Control No.(Change No.IT-0018)
* IT-0018:  Change Filename type from CHAR to ZDCDEFILENAME
*----------------------------------------------------------------------*
* Change Number：004
* Updated On：2021/10/12           Updated By： Yokogawa
* Change Content：
*   ・処理結果ALV-KEY項目のラベルを動的に設定するよう変更
*   ・ALV出力用構造にメッセージ関連の項目を追加
*----------------------------------------------------------------------*
* Change Number：005
* Updated On：2022/03/07           Updated By： Yokogawa
* Change Content：
*   ・機能改善：処理結果の有無に関わらず出力処理を実施するよう変更
*----------------------------------------------------------------------*
* Change Number：006
* Updated On：2022/04/20           Updated By： Seki
* Change Content：
*    OneERP障害管理番号（IT-0008）:アプリケーションログ出力単位を修正
*----------------------------------------------------------------------*
* Change Number：007
* Updated On：2022/06/22           Updated By： Ko sei
* Change Content：
*    IT-0009:アプリログに出力するメッセージテキストの最大文字数を修正
*----------------------------------------------------------------------*
* Change Number：008
* Updated On：2022/08/31           Updated By： Ko sei
* Change Content：
*    変更管理番号(2022-1Q-0030)）:画面表示件数の仕様変更のため、変数設定を修正
*----------------------------------------------------------------------*
* Change Number：009
* Updated On：2022/08/31           Updated By： Orihara
* Change Content：
*    変更管理番号(2022-3Q-0013)）:ログメッセージ編集処理の見直し
*----------------------------------------------------------------------*
* Change Number：010
* Updated On：2023/03/17           Updated By： Imagaki
* Change Content：
*    変更管理番号(2022-4Q-0003)
*----------------------------------------------------------------------*
* Change Number：011
* Updated On：2023/03/17           Updated By： Imagaki
* Change Content：
*    変更管理番号(2022-4Q-0008)
*----------------------------------------------------------------------*
* Change Number：012
* Updated On：2023/04/21           Updated By： Imagaki
* Change Content：
*    変更管理番号(2023-1Q-0004)
*----------------------------------------------------------------------*
* 変更番号：013
* 変更日：2024/03/08           変更者： hori
* 変更内容：選択画面ファイルパス小文字対応
*----------------------------------------------------------------------*

INCLUDE ZDCDF001TOP.

INCLUDE ZDCDF001F01.

* 012(ADD)↓------------------------------------------------
***********************************************************************
INITIALIZATION.
***********************************************************************
PERFORM FM_ZDCDF001_INITIALIZATION.
* 012(ADD)↑------------------------------------------------

***********************************************************************
AT SELECTION-SCREEN ON BLOCK BL_COM1.
***********************************************************************
PERFORM FM_INPUT_CHECK_BL_COM1.
