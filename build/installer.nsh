!macro customInit
  ; Show details (log) during installation — like VLC installer
  SetDetailsPrint both
!macroend

!macro customInstall
  DetailPrint "Installing YT Downloader..."
  DetailPrint "Creating application directory..."
  DetailPrint "Extracting files..."
!macroend

!macro customInstallMode
  ; Force non-silent mode so user always sees the install progress
  StrCpy $isForceRunAsAdmin "true"
!macroend
