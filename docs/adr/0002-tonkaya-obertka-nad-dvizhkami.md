# Тонкая обёртка над готовыми движками

Готовой библиотеки на все наши источники нет (проверены pandas, DuckDB gsheets, frictionless, pyexcel, pytablereader, readwrite, sq). Поэтому dataio — обёртка: pandas, python-calamine (чтение Excel), openpyxl (запись xlsx), DuckDB (parquet, `query=`), sqlite3, gspread. Своё — только адрес, определение формата, умолчания, ошибки и резервные копии.
