import os, sys

os.environ["JAVA_HOME"] = r"C:\Program Files\Eclipse Adoptium\jdk-21.0.13.9-hotspot"
os.environ["PATH"] = os.environ["JAVA_HOME"] + r"\bin;" + os.environ["PATH"]
os.environ["PYSPARK_PYTHON"] = sys.executable

from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .master("local[*]")
    .config("spark.driver.host", "127.0.0.1")
    .config("spark.driver.bindAddress", "127.0.0.1")
    .getOrCreate()
)

df_perso = spark.read.option("multiLine", True).json("../data/personnages_fr.json")
df_perso.show()

display(df_perso.limit(5))
df_perso.show(20)

print(f"Nombre total de personnages : { df_perso.count() }")