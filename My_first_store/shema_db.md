┌─────────────────┐      ┌─────────────────┐
│      User       │      │    Supplier     │
├─────────────────┤      ├─────────────────┤
│ id              │ 1:1  │ id              │
│ username        │ ←─── │ user_id         │
│ email           │      │ name            │
│ user_type       │      │ accepts_orders  │
└─────────────────┘      └─────────────────┘
       │
       │ 1:M
       ▼
┌─────────────────┐      ┌─────────────────┐
│ DeliveryAddress │      │      Order      │
├─────────────────┤      ├─────────────────┤
│ id              │      │ id              │
│ user_id         │      │ user_id         │
│ city            │      │ address_id      │
│ street          │      │ status          │
└─────────────────┘      │ created_at      │
                         └─────────────────┘
                                │
                                │ 1:M
                                ▼
                         ┌─────────────────┐
                         │   OrderItem     │
                         ├─────────────────┤
                         │ id              │
                         │ order_id        │
                         │ product_id      │
                         │ quantity        │
                         └─────────────────┘
                                │
                                │ 1:M
                                ▼
┌─────────────────┐      ┌─────────────────┐
│   Category      │      │     Product     │
├─────────────────┤      ├─────────────────┤
│ id              │      │ id              │
│ name            │ ←─── │ category_id     │
└─────────────────┘      │ supplier_id     │
                         │ name            │
                         │ price           │
                         │ quantity        │
                         │ external_id     │
                         └─────────────────┘
                                │
                                │ 1:M
                                ▼
                         ┌─────────────────┐
                         │ProductParameter │
                         ├─────────────────┤
                         │ id              │
                         │ product_id      │
                         │ parameter_id    │
                         │ value           │
                         └─────────────────┘
                                │
                                │ M:1
                                ▼
                         ┌─────────────────┐
                         │   Parameter     │
                         ├─────────────────┤
                         │ id              │
                         │ name            │
                         └─────────────────┘