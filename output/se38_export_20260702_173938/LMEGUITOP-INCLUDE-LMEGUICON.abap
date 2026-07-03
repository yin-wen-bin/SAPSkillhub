*----------------------------------------------------------------------*
*   INCLUDE LMEGUICON                                                  *
*----------------------------------------------------------------------*
CONSTANTS:

* positions for the header tabs
  c_position_del_payment     TYPE i           VALUE  1,
  c_position_header_cond     TYPE i           VALUE  2,
  c_position_header_texts    TYPE i           VALUE  3,
  c_position_vendor_address  TYPE i           VALUE  4,
  c_position_communication   TYPE i           VALUE  5,
  c_position_partners        TYPE i           VALUE  6,
  c_position_additional_data TYPE i           VALUE  7,
  c_position_header_import   TYPE i           VALUE  8,
  c_position_org_data        TYPE i           VALUE  9,
  c_position_header_status   TYPE i           VALUE 10,
  c_position_header_cust     TYPE i           VALUE 11,
  c_position_rel_info        TYPE i           VALUE 12,
  c_position_iv_fi           TYPE i           VALUE 13,   "EhP4 DP
  c_position_incoterms       TYPE i           VALUE 14,
  c_position_flex_wfl        TYPE i           VALUE 15,
  c_position_header_ptfm     TYPE i           VALUE 16,   "LOCPTFM: OP1709
  c_position_prod_compliance TYPE i           VALUE 17,   "Product Compliance Header


************* Extensibility : PO_GUI/1708 **************************
  c_position_customfield     TYPE i           VALUE 99,
************* Extensibility : PO_GUI/1708 **************************

* positions for the item tabs
  c_position_services        TYPE i           VALUE  1,
  c_position_limits          TYPE i           VALUE  2,
  c_position_material        TYPE i           VALUE  3,
  c_position_uom_weight      TYPE i           VALUE  4,
  c_position_schedules       TYPE i           VALUE  5,
  c_position_item_delivery   TYPE i           VALUE  6,
  c_position_item_payment    TYPE i           VALUE  7,
  c_position_item_conditions TYPE i           VALUE  8,
  c_position_variants        TYPE i           VALUE  9,
  c_position_sls             TYPE i           VALUE 10,
  c_position_brazil          TYPE i           VALUE 11,
  c_position_accountings     TYPE i           VALUE 12,
  c_position_item_status     TYPE i           VALUE 13,
  c_position_po_history      TYPE i           VALUE 14,
  c_position_item_texts      TYPE i           VALUE 15,
  c_position_delivery_addr   TYPE i           VALUE 16,
  c_position_confirmations   TYPE i           VALUE 17,
  c_position_conf_grid       TYPE i           VALUE 18,
  c_position_item_import     TYPE i           VALUE 19,
  c_position_shipping        TYPE i           VALUE 20,
  c_position_cond_control    TYPE i           VALUE 21,
  c_position_retail          TYPE i           VALUE 22,
  c_position_item_cust       TYPE i           VALUE 23,
  c_position_mpn             TYPE i           VALUE 24,
  c_position_itm_incoterms   TYPE i           VALUE 25,
  c_position_itm_prod_compl  TYPE i           VALUE 26,   "Product Compliance Item
  c_position_external_links  TYPE i           VALUE 27,

************* Extensibility : PO_GUI/1708 & PR_GUI/1711**************************
  c_position_item_customfield TYPE i VALUE 99,
************* Extensibility : PO_GUI/1708 & PR_GUI/1711**************************

* positions for the requisition item tabs

  c_req_position_services        TYPE i           VALUE 1,
  c_req_position_limits          TYPE i           VALUE 2,
  c_req_position_material        TYPE i           VALUE 3,
  c_req_position_quantity        TYPE i           VALUE 4,
  c_req_position_valuation       TYPE i           VALUE 5,
  c_req_position_accountings     TYPE i           VALUE 6,
  c_req_position_source          TYPE i           VALUE 7,
  c_req_position_versions        TYPE i           VALUE 8,
  c_req_position_buyer           TYPE i           VALUE 9,
  c_req_position_status          TYPE i           VALUE 10,
  c_req_position_contacts        TYPE i           VALUE 11,
  c_req_position_item_release    TYPE i           VALUE 12,
  c_req_position_item_texts      TYPE i           VALUE 13,
  c_req_position_delivery_addr   TYPE i           VALUE 14,
  c_req_position_item_cust       TYPE i           VALUE 15,
  c_req_position_ext_sourcing    TYPE i           VALUE 16,
  c_req_position_brazil          TYPE i           VALUE 17, "1836886

* View Names
  c_header_conditions TYPE string40 VALUE 'HeaderConditions',
  c_header_iv_fi      TYPE string40 VALUE 'RechnungFI', "#EC *    EhP4 DP
  c_item_conditions  TYPE string40 VALUE 'ItemConditions',  "#EC NOTEXT
  c_services         TYPE string40 VALUE 'Services',        "#EC NOTEXT
  c_limits           TYPE string40 VALUE 'Limits',          "#EC NOTEXT
  c_confirmations    TYPE string40 VALUE 'Confirmations',   "#EC NOTEXT
  c_confirm_grid     TYPE string40 VALUE 'ConfirmationGrid', "#EC NOTEXT
  c_accountings      TYPE string40 VALUE 'Accountings',     "#EC NOTEXT
  c_header_foreign_trade TYPE string40 VALUE 'HeaderImport', "#EC NOTEXT
  c_item_foreign_trade TYPE string40 VALUE 'ItemImport',    "#EC NOTEXT
  c_header_partners  TYPE string40 VALUE 'Partners',        "#EC NOTEXT
  c_item_table       TYPE string40 VALUE 'ItemTable',       "#EC NOTEXT
  c_schedule_table   TYPE string40 VALUE 'ScheduleTable',   "#EC NOTEXT
  c_item_history     TYPE string40 VALUE 'ItemHistory',     "#EC NOTEXT
  c_release          TYPE string40 VALUE 'ReleaseInfo',     "#EC NOTEXT
  c_vendor_address   TYPE string40 VALUE 'Anschrift',       "#EC NOTEXT
  c_delivery_address TYPE string40 VALUE 'Anlieferadresse', "#EC NOTEXT
  c_header_texts     TYPE string40 VALUE 'Kopftexte',       "#EC NOTEXT
  c_brazil           TYPE string40 VALUE 'Brasil',          "#EC NOTEXT  "1836886
  c_brazil_br(2)     TYPE c        VALUE 'BR',              "#EC NOTEXT  "1836886
  c_item_texts       TYPE string40 VALUE 'Positionstexte',  "#EC NOTEXT
  c_variants         TYPE string40 VALUE 'Varianten',       "#EC NOTEXT
  c_sls_item         TYPE string40 VALUE 'SLSPosition',     "#EC NOTEXT
  c_mpn_item         TYPE string40 VALUE 'Materialaustausch', "#EC NOTEXT
  c_source_grid      TYPE string40 VALUE 'Source_Grid',     "#EC NOTEXT
  c_req_item_grid    TYPE string40 VALUE 'ReqItemGrid',     "#EC NOTEXT
  c_po_item_grid     TYPE string40 VALUE 'POItemGrid',      "#EC NOTEXT
  c_out_item_grid    TYPE string40 VALUE 'OutItemGrid',     "#EC *
  c_source_comp      TYPE string40 VALUE 'SourceComposite', "#EC NOTEXT
  c_delivery         TYPE string40 VALUE 'WE/Mahnung',      "#EC NOTEXT
  c_ptfm_vn          TYPE string40 VALUE 'LocPTFMview',     "#EC NOTEXT   "LOCPTFM: OP1709
  c_external_links   TYPE string40 VALUE 'ExternalLinks',   "#EC NOTEXT

*
  megui              LIKE sy-repid VALUE 'SAPLMEGUI',       "#EC NOTEXT
  meviews            LIKE sy-repid VALUE 'SAPLMEVIEWS',     "#EC NOTEXT
  po_views           TYPE mepo_mfs_application
                             VALUE 'MMPUR_PO_VIEWS',        "#EC NOTEXT
  po_doc             TYPE mepo_mfs_application
                             VALUE 'MMPUR_PO_DOC'.          "#EC NOTEXT

" Start: Application Component: IS-AD-ROT, Switch: EAM_AD_REUSE_01, Switch Description: Reuse for Sw Retrofit of ROT/SUB.

* EhP4: moved to common SUB/S2K package
* DI A&D SUB & SPEC2000
constants:
* DI A&D SUB Define position of Spec2000 / Subcontr. view 1339
  c_position_s2k_sc          type i           value 24,
* DI A&D SUB Define position of Spec2000 / Subcontr. view 3339
  c_req_position_s2k_sc          type i           value 240,
* DI A&D SUB Define Spec2000 / Subcontracting view name
  c_s2k_sc          type string40 value 'Spec2000/LB'.       "#EC NOTEXT

" End: Application Component: IS-AD-ROT, Switch: EAM_AD_REUSE_01, Switch Description: Reuse for Sw Retrofit of ROT/SUB.

ENHANCEMENT-POINT LMEGUICON_01 SPOTS ES_SAPLMEGUI STATIC.

" Begin Component: IS-MP-NF, Switch /NFM/MM: NFM Processing MM
* Definition of NF constants for Tabstrips                        "/NFM/
CONSTANTS:                                                        "/NFM/
  c_position_header_nfm   type i         value 80,                "/NFM/
  c_position_item_nfm     type i         value 80,                "/NFM/
  c_header_nfm_vorschl    type string40                           "/NFM/
                          value 'NE-Vorschlagswerte', "#EC NOTEXT "/NFM/
  c_item_nfm_bild         type string40                           "/NFM/
                          value 'NE-Rohstoffverr.'.   "#EC NOTEXT "/NFM/
CONSTANTS:
* DI A&D SUB Define Spec2000 / Subcontracting view name
  c_s2k_sc_nfm          TYPE string40 VALUE 'Spec2000/LB'. "#EC NOTEXT "Apa1698471
" End Component: IS-MP-NF, Switch /NFM/MM: NFM Processing MM

ENHANCEMENT-POINT LMEGUICON_03 SPOTS ES_SAPLMEGUI STATIC.
