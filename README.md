# Pawlygon Utils

A simple blender addon to speed up the creation of facial animation for 3D characters.

## Split Shapekeys

Uses the corresponding vertex groups as a mask to split the shapekey between Left|Right or Upper|Lower. Useful for spliting a "blended shape" as per the Unified Expressions documentation.

https://github.com/user-attachments/assets/9d8f9985-a62f-45c4-9854-a5409fc8d934

## Missing Shapekeys

Lists any missing shapekey from a facial animation standard and gives you a choice to add a blank shapekey with the correct name.

https://github.com/user-attachments/assets/ba3ce357-839b-4720-bf70-9ca4dd715894

_Disclaimer: The unified expression lists only the shapes used in our template and not the complete list._

## Cleanup

Reorders or removes blendshapes ending in ".old".

This is very particular to our workflow. I like to keep a backup of some shapes during development and this helps with cleanup before releasing.
