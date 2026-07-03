*******************************************************************
*   System-defined Include-files.                                 *
*******************************************************************
  INCLUDE lmeguitop.                   " Global Data
  INCLUDE lmeguiuxx.                   " Function Modules

*******************************************************************
*   User-defined Include-files (if necessary).                    *
*******************************************************************
ENHANCEMENT-POINT saplmegui_01 SPOTS es_saplmegui STATIC.
*$*$-Start: SAPLMEGUI_01------------------------------------------------------------------------$*$*
ENHANCEMENT 9  FSH_SAPLMEGUI.    "active version
INCLUDE FSH_ORDER_SCHEDULING_GR_IMPL.
*INCLUDE FSH_PR_SEASON_F4_IMPL.
ENDENHANCEMENT.
ENHANCEMENT 11  OI0_COMMON_SAPLMEGUI.    "active version
* IS-OIL Class implementations
  INCLUDE oi_lmeguicioi.
ENDENHANCEMENT.
ENHANCEMENT 4  OIJ_SAPLMEGUI.    "active version
INCLUDE oi_lmeguicioi_tsw.
ENDENHANCEMENT.
*$*$-End:   SAPLMEGUI_01------------------------------------------------------------------------$*$*
  INCLUDE FSH_PR_SEASON_F4_IMPL.
  INCLUDE lmeguio01.                   " PBO-Modules
  INCLUDE lmeguii01.                   " PAI-Modules
  INCLUDE lmeguif01.
  INCLUDE lmeguici1.                   " Class implementations
  INCLUDE lmeguici2.                   " Class implementations
  INCLUDE lmeguici3.
  INCLUDE lmeguici4.
  INCLUDE lmeguici5.
  INCLUDE lmeguick7.

  INCLUDE lmeguici6.

  INCLUDE lmeguiciq.

  INCLUDE lmeguicir.

  INCLUDE lmeguicis.

  INCLUDE lmeguicit.

  INCLUDE lmeguiciu.

  INCLUDE lmeguiciv.

  INCLUDE lmeguiciw.

  INCLUDE lmeguicix.

  INCLUDE lmeguiciy.

  INCLUDE lmeguiciz.

  INCLUDE lmeguici7.

  INCLUDE lmeguici8.

  INCLUDE lmeguici9.

  INCLUDE lmeguicjm.
  INCLUDE lmeguicjr.
* IL Localization
  INCLUDE /ile/meguixxx.
*
  " Begin Component: IS-MP-NF, Switch /NFM/MM: NFM Processing MM
*Interface for Purchase Orders                 "/NMF/
  INCLUDE /nfm/mm_meguii00.                      "/NFM/
  INCLUDE /nfm/meguif02.                         "/NFM/
  " End Component: IS-MP-NF, Switch /NFM/MM: NFM Processing MM

  INCLUDE ptfm_inc_lmeguici IF FOUND.   " LOCPTFM: OP1709, Class implementation

ENHANCEMENT-POINT saplmegui_03 SPOTS es_saplmegui STATIC.
*$*$-Start: SAPLMEGUI_03------------------------------------------------------------------------$*$*
ENHANCEMENT 1  WRF_SAPLMEGUI_01.    "active version
*------------------------------------------------------------------------------*
* Include for Class Implementation to Handle Dateline Tab (Transportation Chain)
*------------------------------------------------------------------------------*
  INCLUDE wrf_prc_scd_po_cl_imp.
ENDENHANCEMENT.
*$*$-End:   SAPLMEGUI_03------------------------------------------------------------------------$*$*

  INCLUDE lmeguii02.

  INCLUDE lmeguif02.

  INCLUDE lmeguio02.

  INCLUDE lmeguio03.

  INCLUDE lmeguii03.

  INCLUDE lmeguii04.

  INCLUDE lmeguii05.

  INCLUDE lmeguio04.

  INCLUDE mill_megui_top IF FOUND.

  INCLUDE lmeguii06.

  INCLUDE lmeguio05.

  INCLUDE lmeguio06. " note 2471996

  INCLUDE lmeguio07.


INCLUDE lmeguick8.

INCLUDE lmeguii07.

INCLUDE lmeguif04.

INCLUDE lmeguii08.

INCLUDE LMEGUICJ1.

INCLUDE lmeguii09.

INCLUDE lmeguio09.

INCLUDE lmeguii10.

INCLUDE LMEGUII11.

INCLUDE lmeguip01.

INCLUDE lmeguii12.
