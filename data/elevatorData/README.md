# Drop zone for real elevator survey report folders

Put a full report folder here, same shape as the client's own zips:

```
data/elevatorData/
  Binghatti Emerald/
    Binghatti_Emerald.pdf
    Exterior Photos/*.jpg
    Panel/*.jpg
    Elevator Roof Mounting Point/*.jpg
    Roof elevator cell info and speedtest/   (skipped on import -- not site photos)
    Inside elevator cell info and speedtest/  (skipped on import -- not site photos)
```

Nothing in this directory is committed to git (see `.gitignore`) — it holds
real client photos and PDFs, which don't belong in source control. Once a
folder here has been read and imported (`backend/tools/import_report_folder.py`),
its real photos live in `FILE_STORAGE_ROOT` and its data lives in MongoDB —
this directory is just the inbox, not the system of record.
