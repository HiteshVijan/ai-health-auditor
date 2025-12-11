# AI Health Bill Auditor

## Project Structure

```
ai-health-bill-auditor/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── pyproject.toml
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── .gitkeep
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py
│   │   │       ├── endpoints/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── auth.py
│   │   │       │   ├── users.py
│   │   │       │   ├── bills.py
│   │   │       │   ├── audits.py
│   │   │       │   └── uploads.py
│   │   │       └── schemas/
│   │   │           ├── __init__.py
│   │   │           ├── auth.py
│   │   │           ├── user.py
│   │   │           ├── bill.py
│   │   │           └── audit.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py
│   │   │   ├── exceptions.py
│   │   │   └── logging.py
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── bill.py
│   │   │   ├── audit.py
│   │   │   └── line_item.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── user_service.py
│   │   │   ├── bill_service.py
│   │   │   ├── audit_service.py
│   │   │   └── storage_service.py
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   │
│   └── celery_app/
│       ├── __init__.py
│       ├── celery.py
│       ├── config.py
│       └── tasks/
│           ├── __init__.py
│           ├── ocr_tasks.py
│           ├── extraction_tasks.py
│           └── audit_tasks.py
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── .eslintrc.cjs
│   │
│   ├── public/
│   │   ├── favicon.ico
│   │   └── assets/
│   │       └── .gitkeep
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── vite-env.d.ts
│       │
│       ├── api/
│       │   ├── index.ts
│       │   ├── client.ts
│       │   ├── auth.ts
│       │   ├── bills.ts
│       │   └── audits.ts
│       │
│       ├── components/
│       │   ├── common/
│       │   │   ├── Button.tsx
│       │   │   ├── Input.tsx
│       │   │   ├── Modal.tsx
│       │   │   ├── Loader.tsx
│       │   │   └── Table.tsx
│       │   ├── layout/
│       │   │   ├── Header.tsx
│       │   │   ├── Sidebar.tsx
│       │   │   ├── Footer.tsx
│       │   │   └── Layout.tsx
│       │   ├── bills/
│       │   │   ├── BillUpload.tsx
│       │   │   ├── BillList.tsx
│       │   │   ├── BillDetail.tsx
│       │   │   └── BillPreview.tsx
│       │   └── audits/
│       │       ├── AuditResults.tsx
│       │       ├── AuditSummary.tsx
│       │       ├── LineItemTable.tsx
│       │       └── FlaggedItems.tsx
│       │
│       ├── pages/
│       │   ├── Home.tsx
│       │   ├── Login.tsx
│       │   ├── Register.tsx
│       │   ├── Dashboard.tsx
│       │   ├── BillsPage.tsx
│       │   ├── AuditPage.tsx
│       │   └── SettingsPage.tsx
│       │
│       ├── hooks/
│       │   ├── useAuth.ts
│       │   ├── useBills.ts
│       │   ├── useAudits.ts
│       │   └── useUpload.ts
│       │
│       ├── store/
│       │   ├── index.ts
│       │   ├── authSlice.ts
│       │   ├── billSlice.ts
│       │   └── auditSlice.ts
│       │
│       ├── types/
│       │   ├── index.ts
│       │   ├── auth.ts
│       │   ├── bill.ts
│       │   └── audit.ts
│       │
│       ├── utils/
│       │   ├── constants.ts
│       │   ├── formatters.ts
│       │   └── validators.ts
│       │
│       └── styles/
│           ├── globals.css
│           ├── variables.css
│           └── components/
│               └── .gitkeep
│
├── ml/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── model_config.yaml
│   │
│   ├── data/
│   │   ├── raw/
│   │   │   └── .gitkeep
│   │   ├── processed/
│   │   │   └── .gitkeep
│   │   └── interim/
│   │       └── .gitkeep
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── checkpoints/
│   │   │   └── .gitkeep
│   │   └── exports/
│   │       └── .gitkeep
│   │
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py
│   │   ├── ocr_engine.py
│   │   ├── table_extractor.py
│   │   └── preprocessor.py
│   │
│   ├── classification/
│   │   ├── __init__.py
│   │   ├── line_item_classifier.py
│   │   ├── anomaly_detector.py
│   │   └── entity_extractor.py
│   │
│   ├── training/
│   │   ├── __init__.py
│   │   ├── trainer.py
│   │   ├── dataset.py
│   │   ├── transforms.py
│   │   └── metrics.py
│   │
│   ├── inference/
│   │   ├── __init__.py
│   │   ├── predictor.py
│   │   └── pipeline.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── data_utils.py
│       └── visualization.py
│
├── scripts/
│   ├── README.md
│   ├── generate_synthetic_data.py
│   ├── retrain_model.py
│   ├── evaluate_model.py
│   ├── migrate_db.sh
│   ├── seed_database.py
│   ├── export_model.py
│   └── helpers/
│       ├── __init__.py
│       ├── bill_generator.py
│       ├── data_augmentation.py
│       └── cpt_code_utils.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── pytest.ini
│   │
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_api/
│   │   │   ├── __init__.py
│   │   │   ├── test_auth.py
│   │   │   ├── test_bills.py
│   │   │   └── test_audits.py
│   │   ├── test_services/
│   │   │   ├── __init__.py
│   │   │   ├── test_bill_service.py
│   │   │   └── test_audit_service.py
│   │   └── test_models/
│   │       ├── __init__.py
│   │       └── test_bill_model.py
│   │
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_extraction/
│   │   │   ├── __init__.py
│   │   │   ├── test_pdf_extractor.py
│   │   │   ├── test_ocr_engine.py
│   │   │   └── test_table_extractor.py
│   │   ├── test_classification/
│   │   │   ├── __init__.py
│   │   │   ├── test_classifier.py
│   │   │   └── test_anomaly_detector.py
│   │   └── test_inference/
│   │       ├── __init__.py
│   │       └── test_pipeline.py
│   │
│   └── fixtures/
│       ├── sample_bills/
│       │   └── .gitkeep
│       ├── expected_outputs/
│       │   └── .gitkeep
│       └── mock_data.json
│
├── infra/
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   ├── frontend.Dockerfile
│   │   ├── ml.Dockerfile
│   │   └── celery.Dockerfile
│   │
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── ssl/
│   │       └── .gitkeep
│   │
│   ├── minio/
│   │   └── policies/
│   │       └── bucket-policy.json
│   │
│   └── redis/
│       └── redis.conf
│
└── docs/
    ├── api/
    │   └── openapi.yaml
    ├── architecture/
    │   └── system-design.md
    ├── deployment/
    │   └── deployment-guide.md
    └── development/
        └── setup-guide.md
```

