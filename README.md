### Panelizer2PnP

This script takes a `.gerberset` file for a PCB panel produced by [ThisIsNotRocketScience Gerber Panelizer](http://blog.thisisnotrocketscience.nl/projects/pcb-panelizer/), tries to find `.pos` PnP files produced by KiCad for each board in the panel, then merges all the found files for each PCB into a simple `.pos` file with adjusted X and Y coordinates.

How to use:

  - Drag&drop the `.gerberset` file on the main.py. It will create a `.pos` file in the `.gerberset` folder, with the same name as the gerberset file.
  - Run `main.py gerberset_folder\gerberset.gerberset` or `main.py gerberset_folder\` .
  - When running from a script, add an `-s` switch to the commandline to prevent the "press any key to continue" at the end.

Problems:

  - Doesn't support merging separate `.pos` files for top and bottom. Use the "One file per board" option when exporting `.pos` in KiCad.
  - Doesn't have a proper heuristic for occasions when more than one `.pos` file is found in a folder.
  - Doesn't support PCB rotation angles other than 0, 90, -90 and 180 in the `.gerberset` file (need to rotate the component locations accordingly).