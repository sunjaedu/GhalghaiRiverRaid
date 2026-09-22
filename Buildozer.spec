[app]
title = River Raid
package.name = riverraid
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 1
android.hide_titlebar = 1
android.presplash_color = #000000
android.manifest.launch_mode = singleTask

android.api = 34
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
