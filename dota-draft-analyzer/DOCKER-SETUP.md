# Проверка Docker на Windows

Docker Desktop должен показывать Engine running и использовать Linux containers.

Из папки проекта в обычном PowerShell запустите:

```powershell
.\verify-docker.ps1
```

Скрипт собирает образ, обучает обе модели в Linux, запускает FastAPI, Streamlit и MLflow, ждёт готовности сервисов, проверяет прогноз, запускает pytest и Streamlit AppTest внутри контейнеров. Затем проверяет статусы моделей READY, завершение MLflow runs и совпадение загруженных API версий с alias champion. Только после всех проверок записывает PASSED.

Если сборка и обучение уже завершились успешно, повторить проверки без обучения можно так:

```powershell
.\verify-docker.ps1 -Resume
```

Режим Resume требует предыдущий отчёт с подтверждением сборки и обучения. Он сохраняет ссылку на этот отчёт и пересоздаёт сервисы, чтобы загрузить актуальные модели из volume.

Порты проверки: API и Swagger — http://127.0.0.1:18000/docs, интерфейс — http://127.0.0.1:18501, MLflow — http://127.0.0.1:15000. Контейнеры остаются запущенными. Состояние хранится отдельно в docker-state/, отчёты и логи — в docker-evidence/<timestamp>/. Каталог docker-state/ не включается в Git или архив.

Первый полный успешный прогон от 26 ноября 2026: docker-evidence/20261126-171227-438/result.json; 28 тестов прошли, обе модели обучены и зарегистрированы. Итоговый Resume от 26 ноября 2026 также завершён PASSED: docker-evidence/20261126-171746-900/result.json. API обеих моделей загружает champion версии 2; повторно прошли все 28 тестов, прогноз и Registry.

Если Docker сообщает Virtual Machine Platform is not enabled, в PowerShell от администратора выполните:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart
```

При RestartNeeded: True сохраните работу и перезагрузите Windows, затем откройте Docker Desktop. Скрипт проверки не меняет компоненты Windows и не перезагружает компьютер.
