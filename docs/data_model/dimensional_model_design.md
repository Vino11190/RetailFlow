
# RetailFlow — Dimensional Model Design

## 1. Architecture

Warehouse: PostgreSQL 17
Target schema: gold
Modelling approach: Kimball dimensional modelling
Source layer: Bronze Parquet
Transformation layer: Silver PostgreSQL

## 2. Conformed Dimensions

- dim_date: calendar attributes
- dim_product: product attributes; SCD Type 2 candidate
- dim_customer: customer attributes; privacy-aware design
- dim_store: store identifiers from POS and inventory
- dim_supplier: supplier attributes
- dim_channel: e-commerce and POS channel classifications

## 3. Fact Tables

### fact_ecommerce_sales
Grain: One e-commerce order item
Business key: order_item_id
Measures: quantity, unit_price, discount, line_total
Relationships: product, customer, date, channel
Degenerate dimension: order_id

### fact_pos_sales
Grain: One POS transaction record
Business key: transaction_id
Measures: quantity, unit_price, discount, total_amount
Relationships: product, store, date, channel

### fact_payments
Grain: One payment event
Business key: payment_id
Measures: amount
Relationships: date; order_id retained for traceability

### fact_returns
Grain: One return event
Business key: return_id
Measures: quantity, refund_amount
Relationships: product, customer, date
Degenerate dimension: order_id

### fact_inventory_snapshot
Grain: One product-store pair per captured snapshot
Measures: quantity_on_hand, reorder_level
Relationships: product, store, snapshot date

### fact_inventory_movements
Grain: One inventory movement event
Business key: movement_id
Measures: quantity
Relationships: product, store, date

### fact_supplier_deliveries
Grain: One supplier delivery record
Business key: delivery_id
Measures: quantity, calculated delivery delay
Relationships: supplier, product, date

## 4. Modelling Principles

- Use surrogate keys for dimensional relationships.
- Preserve source business keys for traceability.
- Define and enforce fact grain.
- Avoid double-counting order-level measures.
- Use conformed dimensions where source identifiers align.
- Support SCD Type 2 where historical attributes are required.
- Include unknown dimension members where appropriate.
- Avoid inventing unavailable source attributes.
- Handle sensitive customer information appropriately.
- Validate source-to-target reconciliation.

## 5. Implementation Sequence

1. Define detailed dimensional columns and relationships.
2. Create the star schema.
3. Implement surrogate keys and SCD Type 2.
4. Create PostgreSQL Gold DDL.
5. Validate dimensional model constraints.
6. Build Silver-to-Gold transformations in Phase 8.
