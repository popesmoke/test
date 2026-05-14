/*
  Minimal conservative rules — tune for your environment.
  Install yara-python to enable matching (optional).
*/
rule upx_packed_pe {
  strings:
    $upx = "UPX0" ascii
    $upx1 = "UPX1" ascii
  condition:
    uint16(0) == 0x5A4D and 1 of them
}

rule dotnet_reflective_load_hint {
  strings:
    $a = "System.Reflection.Assembly" ascii wide
    $b = "LoadFrom" ascii wide
  condition:
    uint16(0) == 0x5A4D and all of them
}
