CREATE EXTERNAL TABLE your_database.your_table_name (
    json_data string
)
ROW FORMAT SERDE 
  'org.openx.data.jsonserde.JsonSerDe'
STORED AS INPUTFORMAT 
  'org.apache.hadoop.mapred.TextInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat'
LOCATION
  's3://your-bucket/path/to/json/files/'
TBLPROPERTIES (
  'serialization.format' = '1'
);
