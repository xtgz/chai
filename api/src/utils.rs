use serde_json::{json, Value};
use tokio_postgres::types::{Json, Type};
use tokio_postgres::Row;

pub fn get_column_names(rows: &[Row]) -> Vec<String> {
    if let Some(row) = rows.first() {
        row.columns()
            .iter()
            .map(|col| col.name().to_string())
            .collect()
    } else {
        vec![]
    }
}

pub fn rows_to_json(rows: &[Row]) -> Vec<Value> {
    rows.iter()
        .map(|row| {
            let mut map = serde_json::Map::new();
            for (i, column) in row.columns().iter().enumerate() {
                let value: Value = match *column.type_() {
                    Type::INT2 => json!(row.get::<_, i16>(i)),
                    Type::INT4 => json!(row.get::<_, i32>(i)),
                    Type::INT8 => json!(row.get::<_, i64>(i)),
                    Type::FLOAT4 => json!(row.get::<_, f32>(i)),
                    Type::FLOAT8 => json!(row.get::<_, f64>(i)),
                    Type::BOOL => json!(row.get::<_, bool>(i)),
                    Type::VARCHAR | Type::TEXT | Type::BPCHAR => json!(row.get::<_, String>(i)),
                    Type::TIMESTAMP => {
                        let ts: chrono::NaiveDateTime = row.get(i);
                        json!(ts.to_string())
                    }
                    Type::TIMESTAMPTZ => {
                        let ts: chrono::DateTime<chrono::Utc> = row.get(i);
                        json!(ts.to_rfc3339())
                    }
                    Type::DATE => {
                        let date: chrono::NaiveDate = row.get(i);
                        json!(date.to_string())
                    }
                    Type::JSON | Type::JSONB => {
                        let json_value: Json<Value> = row.get(i);
                        json_value.0
                    }
                    _ => Value::Null,
                };
                map.insert(column.name().to_string(), value);
            }
            Value::Object(map)
        })
        .collect()
}
