FUNCTION-POOL megui MESSAGE-ID me.
*
TYPE-POOLS: mmmfd, meatr, szadr, icon, cntb.
"Start : Application Component: IS-AD-ROT,Switch: EAM_AD_REUSE_01, Switch Description: Reuse for Sw Retrofit of ROT/SUB.

** DI A&D: SPEC2000 S1PNSTAT/S1POSTAT screen flag
DATA: s2k_flag TYPE adspc_pnstat.

"End : Application Component: IS-AD-ROT,Switch: EAM_AD_REUSE_01, Switch Description: Reuse for Sw Retrofit of ROT/SUB.
ENHANCEMENT-POINT lmeguitop_01 SPOTS es_saplmegui STATIC.
*$*$-Start: LMEGUITOP_01------------------------------------------------------------------------$*$*
ENHANCEMENT 1  OIJ_SAPLMEGUI.    "active version
*New type pool and table definiion for TSW in MEPO
*type-pools oijc0. SOGK004056 -Manual merge of core objects 22.10.2001
*data  tsw_flag_tab type oijc0_tsw_flag_tab. "SOGK004056
*New table definiions for TSW in MEPO
data:
      itab_oij_el_doc_mot like roij_el_doc_mot
                   occurs 0 with header line,
      G_DOC_M_MOT_ALL TYPE ROIJ_EL_DOC_M_MOT
                    OCCURS 0 WITH HEADER LINE,
      G_DOC_M_MOT_ALL_DEL TYPE ROIJ_EL_DOC_M_MOT
                    OCCURS 0 WITH HEADER LINE,
      gt_doc_i_ref type table of oij_el_doc_i_ref,
      gt_cp_layt type roij_el_cp_layt_t,
      gt_cp_loc type roij_el_cp_loc_t,
      gt_cp_prod type roij_el_cp_prod_t,
      gt_layt_ev type roij_el_layt_ev_t,
      gt_layt_inf type roij_el_layt_inf_t,
      gt_doc_ev type roij_el_doc_ev_t,
      gs_doc_scr type toij_el_doc_mm,
      gt_oijnomr type oijnomr_t.

data: begin of dyn_1302_ext,
              tabstrip31     type string40,
              tabstrip32     type string40,
              tabstrip33     type string40,
              tabstrip34     type string40,
              tabstrip35     type string40.
*             tabstrip36     type string40,
*             tabstrip37     type string40,
*             tabstrip38     type string40,
*             tabstrip39     type string40,
*             tabstrip40     type string40.
data: end of dyn_1302_ext.
ENDENHANCEMENT.
*$*$-End:   LMEGUITOP_01------------------------------------------------------------------------$*$*
INCLUDE lmeguicon.                     "Constants
INCLUDE lmeguitbl.                     "TABLES declarations
*.....................................................................*
CONTROLS: main   TYPE TABSTRIP,
          detail TYPE TABSTRIP.
CONTROLS: item_detail       TYPE TABSTRIP,
          req_item_detail   TYPE TABSTRIP,
          header_detail     TYPE TABSTRIP,
          req_header_detail TYPE TABSTRIP.

* Typ für Tabstrip 30
TYPES: BEGIN OF typ_tab_30,
         tabstrip1  TYPE string40,
         tabstrip2  TYPE string40,
         tabstrip3  TYPE string40,
         tabstrip4  TYPE string40,
         tabstrip5  TYPE string40,
         tabstrip6  TYPE string40,
         tabstrip7  TYPE string40,
         tabstrip8  TYPE string40,
         tabstrip9  TYPE string40,
         tabstrip10 TYPE string40,
         tabstrip11 TYPE string40,
         tabstrip12 TYPE string40,
         tabstrip13 TYPE string40,
         tabstrip14 TYPE string40,
         tabstrip15 TYPE string40,
         tabstrip16 TYPE string40,
         tabstrip17 TYPE string40,
         tabstrip18 TYPE string40,
         tabstrip19 TYPE string40,
         tabstrip20 TYPE string40,
         tabstrip21 TYPE string40,
         tabstrip22 TYPE string40,
         tabstrip23 TYPE string40,
         tabstrip24 TYPE string40,
         tabstrip25 TYPE string40,
         tabstrip26 TYPE string40,
         tabstrip27 TYPE string40,
         tabstrip28 TYPE string40,
         tabstrip29 TYPE string40,
         tabstrip30 TYPE string40,
         tabstrip31 TYPE string40,
         tabstrip32 TYPE string40,
         tabstrip33 TYPE string40,
         tabstrip34 TYPE string40,
         tabstrip35 TYPE string40,
         tabstrip36 TYPE string40,
         tabstrip37 TYPE string40,
         tabstrip38 TYPE string40,
         tabstrip39 TYPE string40,
         tabstrip40 TYPE string40,
         tabstrip41 TYPE string40,
         tabstrip42 TYPE string40,
         tabstrip43 TYPE string40,
         tabstrip44 TYPE string40,
         tabstrip45 TYPE string40,
         tabstrip46 TYPE string40,
         tabstrip47 TYPE string40,
         tabstrip48 TYPE string40,
         tabstrip49 TYPE string40,
         tabstrip50 TYPE string40,
       END OF typ_tab_30.
DATA: dyn_1302 TYPE typ_tab_30,
      dyn_1102 TYPE typ_tab_30,
      dyn_3102 TYPE typ_tab_30,
      dyn_3302 TYPE typ_tab_30.

TYPES: BEGIN OF typ_dyn_6000,
         list(40)      TYPE c,
         list_info(80) TYPE c,
       END OF typ_dyn_6000.

*
* global dynpro data
*

DATA:    dyn_6000            TYPE typ_dyn_6000.

TYPES: BEGIN OF dyn_0011_type,
         ebeln TYPE ekko-ebeln,
       END OF dyn_0011_type.
DATA: dyn_0011 TYPE dyn_0011_type.

CONTROLS: tc_1211 TYPE TABLEVIEW USING SCREEN 1211.    "Items
CONTROLS: tc_1224 TYPE TABLEVIEW USING SCREEN 1224.    "Partners
CONTROLS: tc_1320 TYPE TABLEVIEW USING SCREEN 1320.    "Scheduling lines
CONTROLS: tc_1410 TYPE TABLEVIEW USING SCREEN 1410.    "Items overview for CC
CONTROLS: tc_1420 TYPE TABLEVIEW USING SCREEN 1420.    "Plant Conditions
CONTROLS: tc_3211 TYPE TABLEVIEW USING SCREEN 3211.    "Req-Items
CONTROLS: tc_3214 TYPE TABLEVIEW USING SCREEN 3214.    "APR items
CONTROLS: tc_1351 TYPE TABLEVIEW USING SCREEN 1351.    "External Links

DATA: dyn_1211items TYPE mmpur_models WITH HEADER LINE,  "Items
      dyn_1224items TYPE mmpur_models WITH HEADER LINE,  "Partners
      dyn_1320items TYPE mmpur_models WITH HEADER LINE,  "Sched. lines
      dyn_3211items TYPE mmpur_models WITH HEADER LINE,  "Preq-Items
      dyn_3214items TYPE mmpur_models WITH HEADER LINE,  "APR items
      dyn_1410items TYPE mmpur_models WITH HEADER LINE,  "Items overview for CC
      dyn_1420items TYPE tt_meout1420 WITH HEADER LINE.     "Plant conditions

DATA: dyn_1351items TYPE mmpur_models WITH HEADER LINE. " External Links

DATA: lv_plant TYPE empfw,
      it_a068  TYPE TABLE OF a068,
      wa_a068  TYPE a068,
      it_a081  TYPE TABLE OF a081,
      wa_a081  TYPE a081.

TABLES: megui_range.

*- obs.
DATA: intro_subscreen_program  LIKE sy-cprog VALUE 'SAPLMEGUI',
      main_subscreen_program   LIKE sy-cprog VALUE 'SAPLMEGUI',
      detail_subscreen_program LIKE sy-cprog VALUE 'SAPLMEGUI',
      intro_subscreen_dynnr    LIKE sy-dynnr VALUE '1110',
      main_subscreen_dynnr     LIKE sy-dynnr VALUE '1210',
      detail_subscreen_dynnr   LIKE sy-dynnr VALUE '1319'.
DATA: BEGIN OF excl OCCURS 20,
        fcode LIKE sy-ucomm,
      END OF excl.

DATA:    BEGIN OF fields OCCURS 0.                                "^3216488
        INCLUDE STRUCTURE help_value.
DATA:    END OF fields.

DATA:    BEGIN OF valuetab OCCURS 0,
           value LIKE dfies-fieldtext,
         END   OF valuetab.                                       "v3216488

*------- TKOMV ( Tabelle der Konditionen im Beleg)
DATA:    BEGIN OF tkomv OCCURS 50.
           INCLUDE STRUCTURE komv.
DATA:    END OF tkomv.

TABLES: ekko,  ekpo, eket, rm06e.
TABLES: komk, komp.
TABLES: komg, vake, lfa1, lfm1, t001, t001w.
DATA:  BEGIN OF d1110.
         INCLUDE STRUCTURE mepo1110.
DATA:  END OF d1110.

DATA:  BEGIN OF d1210.
         INCLUDE STRUCTURE mepo1210.
DATA: END OF d1210.

DATA:  BEGIN OF d1222.
         INCLUDE STRUCTURE mepo1222.
DATA: END OF d1222.

DATA:  BEGIN OF d1223.
         INCLUDE STRUCTURE mepo1223.
DATA: END OF d1223.

DATA:  BEGIN OF d1226.
         INCLUDE STRUCTURE mepo1226.
DATA: END OF d1226.

DATA:  BEGIN OF d1229.
         INCLUDE STRUCTURE mepo1229.
DATA: END OF d1229.

DATA: BEGIN OF d1238.                                       "EhP4 DP
        INCLUDE STRUCTURE mepo1238.
DATA: END OF d1238.

DATA:  BEGIN OF d1311.
         INCLUDE STRUCTURE mepo1311.
DATA: END OF d1311.

DATA:  BEGIN OF d1312.
         INCLUDE STRUCTURE mepo1312.
DATA: END OF d1312.

DATA:  BEGIN OF d1313.
         INCLUDE STRUCTURE mepo1313.
DATA: END OF d1313.

DATA:  BEGIN OF d1314.
         INCLUDE STRUCTURE mepo1314.
DATA: END OF d1314.

DATA:  BEGIN OF d1319.
         INCLUDE STRUCTURE mepo1319.
DATA: END OF d1319.

DATA:  BEGIN OF d1320.
         INCLUDE STRUCTURE mepo1320.
DATA: END OF d1320.

DATA:  BEGIN OF d1321.
         INCLUDE STRUCTURE mepo1321.
DATA: END OF d1321.

DATA:  BEGIN OF d1322.
         INCLUDE STRUCTURE mepo1322.
DATA: END OF d1322.

DATA:  BEGIN OF d1323.
         INCLUDE STRUCTURE mepo1323.
DATA: END OF d1323.

*ATA:  BEGIN OF d1332.
*       INCLUDE STRUCTURE mepo1332.
*ATA: END OF d1332.

DATA: gf_tpo_act_sel_line LIKE sy-stepl.
DATA: gf_tpo_top_line_1210 LIKE sy-stepl.
DATA: gf_tpo_line LIKE sy-stepl.
DATA: gf_tpo_field LIKE sy-sfnam.
*TYPES:
*  BEGIN OF TY_ITEM,
*    ITEM   TYPE MEPO1210.
*TYPES: SCHEDULES LIKE MEPO1320 OCCURS 0,
*  END OF TY_ITEM.



*DATA:  TPO TYPE TY_ITEM OCCURS 0 WITH HEADER LINE. "Positionen
DATA:  tpo LIKE d1210 OCCURS 0 WITH HEADER LINE. "Positionen

DATA: gf_tet_act_sel_line LIKE sy-stepl.
DATA: gf_tet_top_line_1320 LIKE sy-stepl.
DATA: gf_tet_line LIKE sy-stepl.
DATA: gf_tet_field LIKE sy-sfnam.
DATA:  tet LIKE d1320 OCCURS 0 WITH HEADER LINE. "Einteilungen

DATA:  t_ss LIKE mepo1220_nav OCCURS 0 WITH HEADER LINE."Navigation Sub

DATA: ok-code LIKE sy-ucomm.

DATA: changedis(30),
      createnew(30),
      changeobj(30),
      dispvend(30),
      searchobj(30),
      header(30),
      overview(30),
      position(30),
      standarddetail(30),
      organisation(30),
      kommunikation(30),
      partner(30),
      incoterms(30),
      zahlungsbedingungen(30),
      laufzeit(30),
      fristen(30),
      sonstiges(30),
      umrechnung(30),
      gewicht(30),
      mahnen(30),
      bestaetigung(30),
      termine(30),
      dispo(30),
      we_re(30),
      steuern(30),
      material(30),
      htn(30),
      handel(30),
      versand(30).

DATA: ext_rfc VALUE 'X'.

DATA: tpo_error_field     LIKE sy-sfnam,
      tpo_error_handle    LIKE sy-tabix,
      tpo_error_on_detail.
DATA: tet_error_field     LIKE sy-sfnam,
      tet_error_handle    LIKE sy-tabix,
      tet_error_on_detail.

DATA: header_aktyp.
DATA: actual_document LIKE ekko-ebeln, actual_aktyp,
      actual_item     LIKE ekpo-ebelp,
      last_document   LIKE ekko-ebeln, last_aktyp,
      next_document   LIKE ekko-ebeln, next_aktyp.
*
DATA: lf_1100    LIKE sy-dynnr,
      lf_1200    LIKE sy-dynnr,
      lf_1300    LIKE sy-dynnr,
      lf_1222    LIKE sy-dynnr,
      lf_1223    LIKE sy-dynnr,
      lf_1224    LIKE sy-dynnr,
      lf_1226    LIKE sy-dynnr VALUE '1226',
      lf_1238    LIKE sy-dynnr VALUE '1238',                  "EhP4 DP
      lf_1229    LIKE sy-dynnr,
      lf_1311    LIKE sy-dynnr VALUE '1311',
      lf_1312    LIKE sy-dynnr VALUE '1312',
      lf_1313    LIKE sy-dynnr,
      lf_1314    LIKE sy-dynnr,
      lf_1317    LIKE sy-dynnr,
      lf_1318    LIKE sy-dynnr VALUE '1318',
      lf_1319    LIKE sy-dynnr,
      lf_1321    LIKE sy-dynnr,
      lf_1322    LIKE sy-dynnr,
      lf_1323    LIKE sy-dynnr,
      lf_taxes   LIKE sy-dynnr VALUE '1005',
      lf_replan  LIKE sy-dynnr VALUE '1006',
      lf_partner LIKE sy-dynnr VALUE '7777',
      lf_program LIKE sy-repid VALUE 'SAPLMEGUI'.
DATA  status.                          "Teilbereich auf/zu
DATA: gf_header_cum_1 LIKE sy-dynnr,
      gf_header_cum_2 LIKE sy-dynnr.

*
CONSTANTS: c_id1220(4)    TYPE c VALUE '1220',
           c_id1000(4)    TYPE c VALUE '1000',
           c_id1310(4)    TYPE c VALUE '1310',
           c_screen1220   LIKE sy-dynnr VALUE '1220',
           c_1000         LIKE sy-dynnr VALUE '1000',
           c_1001         LIKE sy-dynnr VALUE '1001',
           c_1002         LIKE sy-dynnr VALUE '1002',
           c_1003         LIKE sy-dynnr VALUE '1003',
           c_1004         LIKE sy-dynnr VALUE '1004',
           c_1005         LIKE sy-dynnr VALUE '1005',
           c_1006         LIKE sy-dynnr VALUE '1006',
           c_1100         LIKE sy-dynnr VALUE '1100',
           c_1200         LIKE sy-dynnr VALUE '1200',
           c_1201         LIKE sy-dynnr VALUE '1201',
           c_1300         LIKE sy-dynnr VALUE '1300',
           c_1310         LIKE sy-dynnr VALUE '1310',
           c_1222         LIKE sy-dynnr VALUE '1222',
           c_1223         LIKE sy-dynnr VALUE '1223',
           c_1224         LIKE sy-dynnr VALUE '1224',
           c_1226         LIKE sy-dynnr VALUE '1226',
           c_1229         LIKE sy-dynnr VALUE '1229',
           c_1238         LIKE sy-dynnr VALUE '1238',               "EhP4 DP
           c_1311         LIKE sy-dynnr VALUE '1311',
           c_1312         LIKE sy-dynnr VALUE '1312',
           c_1313         LIKE sy-dynnr VALUE '1313',
           c_1314         LIKE sy-dynnr VALUE '1314',
           c_1317         LIKE sy-dynnr VALUE '1317',
           c_1318         LIKE sy-dynnr VALUE '1318',
           c_1319         LIKE sy-dynnr VALUE '1319',
           c_1321         LIKE sy-dynnr VALUE '1321',
           c_1322         LIKE sy-dynnr VALUE '1322',
           c_1323         LIKE sy-dynnr VALUE '1323',
           c_7777         LIKE sy-dynnr VALUE '7777',
           c_partner      LIKE sy-dynnr VALUE '0201',
           c_ekpa         LIKE sy-repid VALUE 'SAPLEKPA',
           c_megui        LIKE sy-repid VALUE 'SAPLMEGUI',
           open           VALUE '1',             "Teilbereich aufgeklappt
           closed         VALUE '2',           "Teilbereich geschlossen
           c_max_gwert    LIKE mepo1312-ntgew_g             "373054
                             VALUE '999999999999.999',   "Obergrenze
           c_repl         LIKE sy-tcode VALUE 'MEPO1317REPL',    "Re-Plan
           c_taxes        LIKE sy-tcode VALUE 'MEPO1317TAX',    "Steuern
           c_bom          LIKE sy-tcode VALUE 'MEPO1319BOM',    "Stückliste
           c_config       LIKE sy-tcode VALUE 'MEPO1319CONFIG', "Konfiguration
           c_bom_exp      LIKE sy-tcode VALUE 'MEPO1319BOMEXP', "Stüli-Auflös.
           c_create_batch LIKE sy-tcode VALUE 'MEPO1319CRBA', "Batch an
           c_req_bom      LIKE sy-tcode VALUE 'MEREQ3319BOM', "Stückliste
*Konfiguration
           c_req_config   LIKE sy-tcode VALUE 'MEREQ3319CONFIG',
           c_sel_char     LIKE sy-tcode VALUE 'MEPO1319SEL_CHAR', "Klassifiz.
*Stüli-Auflös
           c_req_bom_exp  LIKE sy-tcode VALUE 'MEREQ3319BOMEXP',
           c_req_avail    LIKE sy-tcode VALUE 'MEREQ3321AVAIL',
           c_br_lfd       LIKE sy-tcode VALUE 'MEPO1326LFD'. "Brazilian Local Fiscal Data

DATA: refe TYPE i.
* Varianten
DATA: gtvar LIKE evarart OCCURS 0 WITH HEADER LINE.

* conditions
* contains conditions of the header and conditions of one item
DATA: gt_komv LIKE komv OCCURS 0 WITH HEADER LINE.
* flag: conditions on header screen were changed
DATA: gf_header_conditions_changed TYPE xfeld.
* flag: conditions of the item were changed
DATA: gf_item_conditions_changed TYPE xfeld.
* calculation type which was selected on the header condition screen
DATA: gf_header_calculation_type LIKE komv-ksteu.

* tooltips
DATA: tooltip_quantity1(40) TYPE c,
      tooltip_quantity2(40) TYPE c,
      tooltip_quantity3(40) TYPE c,
      tooltip_quantity4(40) TYPE c,
      tooltip_value1(40)    TYPE c,
      tooltip_value2(40)    TYPE c,
      tooltip_value3(40)    TYPE c,
      tooltip_value4(40)    TYPE c,
      tooltip_value5(40)    TYPE c,
      tooltip_ltsbz(100)    TYPE c.

INCLUDE fmmexdir.
INCLUDE mm_messages_mac.
INCLUDE lmeguicd6.                     " Class definitions
INCLUDE lmeguicd1.                     " Class definitions
INCLUDE lmeguicd2.                     " Class definitions
INCLUDE lmeguicd3.                     " Class definitions
INCLUDE lmeguicd4.                     " Class definitions
INCLUDE lmeguicd5.                     " Class definitions
INCLUDE lmeguicd7.                     " Class definitions
INCLUDE lmeguicd8.                     " Class definitions
INCLUDE lmeguicd9.                     " Class definitions
INCLUDE lmeguid05. "Class Definition CCM
INCLUDE lmeguicdq.                     " Class definitions
INCLUDE lmeguicdr.                     " Class definitions
INCLUDE lmeguicds.                     " Class definitions
INCLUDE lmeguicdt.                     " Class definitions
INCLUDE lmeguicdu.                     " Class definitions
INCLUDE lmeguicdv.                     " Class definitions
INCLUDE lmeguicdw.                     " Class definitions
INCLUDE lmeguicdx.                     " Class definitions
INCLUDE lmeguicdy.                     " Class definitions
INCLUDE lmeguicdz.                     " Class definitions
INCLUDE lmeguicda.                     " Class definitions
INCLUDE lmeguice1.                     " Class definitions
INCLUDE lmeguicdb.                     " Class definitions
INCLUDE lmeguice2.                     " Class definitions
INCLUDE lmeguice3.                     " Class definitions
INCLUDE lmeguice4.                     " Class definitions
INCLUDE lmeguice5.                     " Class definitions
INCLUDE lmeguice6.                     " Class definitions
INCLUDE lmeguice7.                     " Class definitions
INCLUDE lmeguice8.                     " Class definitions
INCLUDE lmeguice9.                     " Class definitions
INCLUDE lmeguicf1.                     " Class definitions
INCLUDE lmeguicf2.                     " Class definitions
INCLUDE lmeguicf3.                     " Class definitions
INCLUDE lmeguicf4.                     " Class definitions
INCLUDE lmeguicf5.                     " Class def.       "1836886
INCLUDE lmeguicf6.
INCLUDE lmeguicf7.

* IL Localization
*" Class definitions for annexing data
INCLUDE /ile/meguicd01.       " class for header
INCLUDE /ile/meguicd02.       " class for item
INCLUDE /ile/meguicd03.       " class for ann. package header
INCLUDE /ile/meguicd04.       " class for ann. package item
*
INCLUDE ptfm_inc_lmeguicd IF FOUND.    " LOCPTFM: OP1709, Class definition
*
ENHANCEMENT-POINT lmeguitop_03 SPOTS es_saplmegui STATIC.
*$*$-Start: LMEGUITOP_03------------------------------------------------------------------------$*$*
ENHANCEMENT 10  OI0_COMMON_SAPLMEGUI.    "active version
INCLUDE oi_lmeguitoi.
ENDENHANCEMENT.
ENHANCEMENT 5  OIJ_SAPLMEGUI.    "active version
include oi_lmeguicdoi_tsw.
ENDENHANCEMENT.
*$*$-End:   LMEGUITOP_03------------------------------------------------------------------------$*$*


" Begin Component: IS-MP-NF, Switch /NFM/MM: NFM Processing MM
*for NF-active check                                              "/NFM/
*data: /nfm/g_tbasic like /nfm/tbasic.                            "/NFM/
INCLUDE /nfm/sapmm06e_top.            "NE-Datendefinitionen       "/NFM/
*NF Class Definitions                                             "/NFM/
INCLUDE /nfm/mm_meguid01.                                         "/NFM/
" End Component: IS-MP-NF, Switch /NFM/MM: NFM Processing MM

ENHANCEMENT-POINT lmeguitop_04 SPOTS es_saplmegui STATIC.
*$*$-Start: LMEGUITOP_04------------------------------------------------------------------------$*$*
ENHANCEMENT 8  FSH_VAS_SAPLMEGUI.    "active version
INCLUDE FSH_VAS_TOP.
INCLUDE FSH_DEALLOC_TOP.
INCLUDE FSH_ORDER_SCHEDULING_GR_DEF.
INCLUDE FSH_DC_MEGUI.
*INCLUDE FSH_PR_SEASON_F4_DEF.
ENDENHANCEMENT.
ENHANCEMENT 1  WRF_LMEGUITOP_01.    "active version
*--------------------------------------------------------------------------*
* Include for Class Definition to Handle Dateline Tab (Transportation Chain)
*--------------------------------------------------------------------------*
  INCLUDE wrf_prc_scd_po_cl_def.

ENDENHANCEMENT.
*$*$-End:   LMEGUITOP_04------------------------------------------------------------------------$*$*
INCLUDE fsh_pr_season_f4_def.
* DIMP IS MILL ENHANCEMENTS FOR FDE
INCLUDE mill_megui_top IF FOUND.


DATA: /sapmp/scope      TYPE /sapmp/ce_scope.
DATA: /sapmp/muebs TYPE  muebs,
      /sapmp/gpose TYPE  mepoitem-/sapmp/gpose.
DATA: go_mill_enh TYPE REF TO lcl_po_mill_enh.
DATA: gv_fde_check TYPE flag.

DATA: tctrl_column TYPE cxtab_column.

CONSTANTS:badiname(20)      TYPE c VALUE 'ME_CIP_ALLOW_CHANGE'.


CLASS cl_exithandler DEFINITION LOAD.
DATA exit_me_cip_allow_change TYPE REF TO if_ex_me_cip_allow_change.
** Datencontainer for items
* Tabelle der Merkmalswerte auf dem Übersichtsbild
DATA: BEGIN OF wa_xmwert,
        id        TYPE mepoitem-id,
        posnr     TYPE ebelp,
        gpose     TYPE ebelp,
        cuobj     TYPE inob-cuobj,
        ch_check  TYPE flag,   "auf Änderbarkeit geprüft und im buffer
        display   TYPE flag,   "changes not allowed
        no_config TYPE flag,   "material isn't configurable
        first     TYPE flag,   "first run for item
        obsolete  TYPE flag,   "values are obsolete
        input_ok  TYPE flag,   "input is okay
        changed   TYPE flag,   "configuration is changed
      END OF wa_xmwert.
*DATA: xmwert LIKE TABLE OF wa_xmwert.
INCLUDE mill_se_const IF FOUND.
DATA: g_icon_conf       TYPE statusicon,
      g_icon_change     TYPE statusicon,
      g_icon_display    TYPE statusicon,
      g_icon_locked_vc  TYPE statusicon,
      g_icon_locked     TYPE statusicon,
      g_icon_incomplete TYPE statusicon,
      g_icon_failure    TYPE statusicon.
* Constants for fast data entry
INCLUDE <icon>.
INCLUDE /sapmp/ce_constants IF FOUND.
INCLUDE /sapmp/ce_data1 IF FOUND.
INCLUDE /sapmp/ce_data2 IF FOUND.
* DIMP IS MILL ENHANCEMENTS FOR FDE
