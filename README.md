# AutoBackupCRR
Easy to configure automation to copy backups of AWS resources (EC2, RDS) from one region to another (Cross Region Replication)
It uses CloudFormation and Lambda (Python 3.8)

It will copy AMIs or EBS Snapshots, and RDS (including Aurora) Snapshots with a specified Tag and Value from a source region to another region. (This could help on keeping a pilot-light Multi-Region site)

If it's not working on your Region create an Issue and I will fix it.

> Version 1.0.0

### Files:
- autoBackupCRR-template.yml, CloudFormation template to Run in your account in Source Region, it is already in a public S3 bucket

- autobackupcrr.py, Lambda code that actually do the job of copying the backups, source code only for reviewing

- autobackupcrr.zip, Zip file used by the template to deploy de Lambda, it is already in a public S3 Bucket

## How To Deploy
Use AWS CloudFormation to deploy the following template:

https://higher-artifacts.s3.amazonaws.com/autoBackupCRR-template.yml

### Parameters:
- *Env Tag*, use to identified the components of the template

- *Selection Tag Key*, sets the Tag used to identify the resources to copy

- *Selection Tag Value*, sets the Value of the Tag to identify the resources to copy

- *Frequency*, specify how often the "copy process" will run (in days)

- *Time*, specify at what time the "copy process" will run (UTC 24 hours syntax)

- *Destination Region*, specify to which region the copies will be replicated, the Source Region is where you deploy the CFN template

- *EC2 Resource*, select which type of backup you want to copy, Instance Images (AMI) or EBS Snapshots (Snapshot)

`If you edit the template remember to use LF end of lines.`

`Update KMS user policy to include Lambda Role if using KMS encrypted EBSs.`

#### Notes:
- Deployable on Source Region

- Function DOES copy AMIs or EBS Snapshots, with a defined Tag, from source Region to another 

- Function DOES copy RDS Snapshots (includes Aurora), with a defined Tag, from source Region to another

- Function DOES copy Encrypted resources but they will be encrypted on destination with default AWS Managed CMKs (aws/*)

- Function DOES NOT replicate deletions

- Function DOES NOT replicate Shared or Public Snapshots

- Function DOES NOT replicate RDS snapshots for DB instance that uses Transparent Data Encryption for Oracle or Microsoft SQL Server

## To-Do
- Make a more restrict EC2/RDS policy for the Lambda so it can only copy the needed resources

- A better error management

- Possibility to use own CMK to encrypt the resources on the destination region
