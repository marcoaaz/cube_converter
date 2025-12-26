# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=["helperFunctions", "."],
    binaries=[],
    datas=[
        ("icons", "icons"),
        ("E:/Alienware_March 22/current work/00-new code May_22/vsiFormatter/vsi_trial1/Lib/site-packages/javabridge/jars/*", "javabridge/jars"), 
        ("E:/Alienware_March 22/current work/00-new code May_22/vsiFormatter/vsi_trial1/Lib/site-packages/javabridge/*", "javabridge"),
        ("E:/Alienware_March 22/current work/00-new code May_22/vsiFormatter/vsi_trial1/Lib/site-packages/bioformats/jars/*", "bioformats/jars"),                
        ("E:/Alienware_March 22/current work/00-new code May_22/vsiFormatter/vsi_trial1/Lib/site-packages/bioformats/*", "bioformats"),
        ("c:/vips-dev-8.16/bin", "vips"),
        ("C:/Program Files/Amazon Corretto/jdk1.8.0_462", "jdk_folder_in_bundle")
        ],
    hiddenimports=[
        'xsdata_pydantic_basemodel.hooks', 
        'xsdata_pydantic_basemodel.hooks.class_type',
        'bioformats', 'javabridge'
        ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,    
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Cube Converter v1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, #javabridge.jvm issue
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icons/cube_icon.ico"
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Cube Converter v1',
)
