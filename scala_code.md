import java.io.{File, FileOutputStream, InputStream}
import org.apache.commons.io.IOUtils
import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.security.UserGroupInformation
import org.apache.http.impl.client.CloseableHttpClient
import org.apache.http.impl.client.HttpClients
import org.apache.http.client.methods.HttpGet
import org.apache.http.util.EntityUtils
import org.apache.spark.sql.SparkSession

import com.amazonaws.auth.DefaultAWSCredentialsProviderChain
import com.amazonaws.services.s3.AmazonS3ClientBuilder
import com.amazonaws.services.s3.model.GetObjectRequest

object KerberosHttpGlueJob {

  def main(args: Array[String]): Unit = {

    // Initialize SparkSession in AWS Glue environment
    val spark = SparkSession.builder()
      .appName("Kerberos HTTP Glue Job")
      .getOrCreate()

    // S3 bucket and keys (adjust as necessary)
    val s3Bucket = "<<S3 bucket>>"
    val keytabKey = "<<file key for keytab>>"
    val krb5ConfKey = "<<file key for krb5.conf>>"

    // Build S3 client
    val s3Client = AmazonS3ClientBuilder.standard()
      .withRegion("us-east-1")
      .withCredentials(DefaultAWSCredentialsProviderChain.getInstance())
      .build()

    // Temporary files for keytab and krb5.conf
    val keytabFile = File.createTempFile("temp_keytab", ".keytab")
    val krb5ConfFile = File.createTempFile("temp_krb5", ".conf")

    var keytabInputStream: InputStream = null
    var keytabOutput: FileOutputStream = null
    var krb5ConfInputStream: InputStream = null
    var krb5ConfOutput: FileOutputStream = null

    try {
      // Download and write keytab file
      val keytabObject = s3Client.getObject(new GetObjectRequest(s3Bucket, keytabKey))
      keytabInputStream = keytabObject.getObjectContent
      keytabOutput = new FileOutputStream(keytabFile)
      IOUtils.copy(keytabInputStream, keytabOutput)

      // Download and write krb5.conf
      val krb5ConfObject = s3Client.getObject(new GetObjectRequest(s3Bucket, krb5ConfKey))
      krb5ConfInputStream = krb5ConfObject.getObjectContent
      krb5ConfOutput = new FileOutputStream(krb5ConfFile)
      IOUtils.copy(krb5ConfInputStream, krb5ConfOutput)

      println("Keytab and krb5.conf downloaded successfully!")

      // Close file streams
      keytabOutput.close()
      krb5ConfOutput.close()
      keytabInputStream.close()
      krb5ConfInputStream.close()

      // Set Kerberos configuration
      System.setProperty("java.security.krb5.conf", krb5ConfFile.getAbsolutePath)

      // Hadoop configuration for Kerberos
      val conf = new Configuration()
      conf.set("hadoop.security.authentication", "kerberos")
      UserGroupInformation.setConfiguration(conf)

      // Login using keytab
      // NOTE: Replace "your-service-principal" with your actual Kerberos principal (e.g., user@REALM)
      UserGroupInformation.loginUserFromKeytab("your-service-principal", keytabFile.getAbsolutePath)
      println("Kerberos authentication successful")

      // HTTP Request Setup
      // If this URL requires Kerberos/SPNEGO auth, you may need to configure HttpClient accordingly.
      val url = "<<client url>>"

      val client: CloseableHttpClient = HttpClients.createDefault()
      val httpGet = new HttpGet(url)

      // Execute HTTP GET Request
      val response = client.execute(httpGet)
      val responseString = EntityUtils.toString(response.getEntity)
      println(s"HTTP Response: $responseString")

      // Process the response as needed...

    } finally {
      // Ensure resources are closed and temporary files are removed
      if (keytabOutput != null) keytabOutput.close()
      if (krb5ConfOutput != null) krb5ConfOutput.close()
      if (keytabInputStream != null) keytabInputStream.close()
      if (krb5ConfInputStream != null) krb5ConfInputStream.close()

      keytabFile.delete()
      krb5ConfFile.delete()
    }
  }
}


Below are the dependencies and detailed configuration steps for running the provided Scala code as an AWS Glue job:

### Dependencies

The code uses several libraries not available by default in AWS Glue (depending on your Glue version). To ensure smooth execution, you need the following:

1. **AWS SDK for S3**:  
   Allows the code to fetch the keytab and krb5.conf files from Amazon S3.  
   **Maven coordinates**: `com.amazonaws:aws-java-sdk-s3`

2. **Apache Commons IO**:  
   Used here for copying streams (IOUtils.copy).  
   **Maven coordinates**: `commons-io:commons-io`

3. **Apache HttpClient**:  
   Provides the HTTP client for making the HTTP GET request.  
   **Maven coordinates**: `org.apache.httpcomponents:httpclient`

4. **Hadoop Common and Hadoop Auth** (Likely already available in Glue):  
   Kerberos authentication (`UserGroupInformation`) classes are part of Hadoop’s authentication libraries. AWS Glue generally includes Hadoop libraries, but if not, you may need:  
   **Maven coordinates**: 
   - `org.apache.hadoop:hadoop-common`  
   - `org.apache.hadoop:hadoop-auth`

**Note:** In most AWS Glue environments (especially Glue 3.0 and 4.0), Hadoop and some AWS SDK components are already available. For Glue 4.0, you have Hadoop 3.3.1 and a fairly complete AWS SDK environment. However, you may still need `commons-io` and `httpclient`.

### Packaging Dependencies

**Option 1: Fat (Uber) JAR**  
The easiest approach is to create a single JAR file containing all dependencies along with your compiled Scala code.  
- Use Maven Shade Plugin or sbt-assembly to create a "fat" JAR that includes all dependencies.  
- After packaging, you will have one JAR that you can directly use in AWS Glue without specifying extra jars.

**Option 2: Individual JARs**  
If you prefer not to create a fat JAR:
- Package your Scala code into a JAR without dependencies.
- Upload any required dependencies (like `commons-io.jar` and `httpclient.jar`) to S3.
- When creating or updating the Glue job, specify these JARs under `--extra-jars`.

### AWS Glue Job Configuration Steps

1. **Create or Update Your IAM Role**:  
   - Make sure the IAM role used by your Glue job has `s3:GetObject` permissions for the buckets containing:
     - The JAR file(s).
     - The `keytab` and `krb5.conf` files.
   - If Kerberos authentication requires access to a Key Distribution Center (KDC), ensure that the network environment allows that access.

2. **Upload the JAR(s) to S3**:  
   - If using a fat JAR, upload just the single JAR (for example, `my-job-assembly.jar`) to an S3 location: `s3://my-bucket/jars/my-job-assembly.jar`.
   - If using individual JARs, upload them all to S3, e.g.:
     - `s3://my-bucket/jars/my-job.jar` (your code)
     - `s3://my-bucket/jars/httpclient.jar`
     - `s3://my-bucket/jars/commons-io.jar`
     - (Hadoop and AWS SDK may already be available in Glue, so you might skip these.)

3. **Specify the Job in AWS Glue**:  
   - Go to the AWS Glue console and create a new Glue job (or edit an existing one).
   - Set the "Script location" to the JAR (if using Scala JAR as a job script) or if running as an ETL job, specify the location in the "Job details".
   - Under "Advanced properties" (in the Glue job console), find "Job parameters".
   - If you used a fat JAR, you don’t need `--extra-jars`; just use the single JAR.
   - If using multiple JARs, add a parameter:  
     `--extra-jars s3://my-bucket/jars/httpclient.jar,s3://my-bucket/jars/commons-io.jar`
   
   For Glue versions:
   - **Glue 4.0** already includes Hadoop 3.3.1 and AWS SDK for Java, so you may only need `commons-io` and `httpclient`.
   - If any library is missing, just add it to `--extra-jars`.

4. **Set the Glue Job Parameters** (if required):  
   When running the job:
   - No special arguments might be needed unless your code references arguments from `args`.
   - Ensure that the environment variables or system properties (like `java.security.krb5.conf`) can be set. In the code, you set `System.setProperty("java.security.krb5.conf", krb5ConfFile.getAbsolutePath)`, which should be fine.

5. **Run the Job**:  
   Start the job in the Glue console.  
   - Check CloudWatch Logs for any errors.
   - If you receive ClassNotFound exceptions, verify that the required JARs are included.
   - If Kerberos login fails, ensure your principal and keytab are correct and that `krb5.conf` is valid.

### Additional Considerations

- **Kerberos Accessibility**:  
  Ensure the Glue job environment can reach your KDC. Glue typically runs in a private network within AWS. If your KDC is external, you may need a VPN or Direct Connect. If your KDC is internal, ensure DNS is correct and `krb5.conf` points to the correct realm and KDC.

- **Principal and Keytab**:  
  The principal used in `UserGroupInformation.loginUserFromKeytab("your-service-principal", ...)` must match exactly the one in the keytab. For example, `myuser@EXAMPLE.COM`.

- **SPNEGO/HTTP Kerberos Authentication**:  
  If the target URL requires SPNEGO for Kerberos-based HTTP authentication, additional configuration is needed on the HttpClient. This might include adding `httpclient-spnego` integration, setting up AuthSchemeProviders, and verifying that the TGT from the keytab login is accessible to the HttpClient. This is not trivial and may require including additional dependencies and code.

By following these steps and including the required dependencies, you should be able to run the Scala Kerberos-enabled HTTP job in AWS Glue.
