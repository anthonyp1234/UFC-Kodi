##UFC APP for KODI
They changed the whole API for UFC in 2020, so I rewrote an app for KODI for the UFC.

Place in your kodi addon folder under a new folder called "plugin.video.ufc"
in unix its .kodi/addon/plugin.video.ufc

Currently it grabs the different directories (from the UFC website) and displays them in a menu.
It's able to drill down the folder structure (i.e. if there's a folder for Nate Diaz or Connor Mcgregor or Khabib the eagle on the UFC website, then it should display the playlist as a folder you can drill into).
It also plays the vids as well.
I've also got live working, please note I have NOT tested it with purchased live events so don't rely on this (it may or may not work....please let me know if you try it).
Added search now also.


Use the setting for the app to put in your username and password, and also the resolution you want to stream (you can select 1080, 720, 504 etc)

Oh and if the UFC see this and feel like giving me some Kudos, how about some free close to the ring tickets for me and the guys at my gym here in Melbourne next time the UFC is in Melbourne :) (thought I'd give it a shot)

Updated now to properly handle split audio/video streams (HLS). 
Now uses "script.module.inputstreamhelper" which needs to be installed from kodi repos.
Use this script to select the bandwidth you wish to use for adaptive streaming (it will change the stream automagically depending on your BW)



