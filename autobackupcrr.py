# igarcia 2019-11
# Version 0.5
# Deployable on Source Region
# Function DOES copy AMIs or EBS Snapshots, with a defined Tag, from source Region to another 
# Function DOES copy RDS Snapshots (includes Aurora), with a defined Tag, from source Region to another
# Function DOES copy Encrypted resources but they will be encrypted on destination with default AWS Managed CMKs (aws/*)
# Function DOES NOT replicate deletions
# Function DOES NOT replicate Shared or Public Snapshots
# Function DOES NOT replicate RDS snapshots for DB instance that uses Transparent Data Encryption for Oracle or Microsoft SQL Server

import boto3
import datetime
import json
import os
import uuid

S_REGION = os.environ['SREGION']    # Source Region
D_REGION = os.environ['DREGION']    # Destination Region
TAGGENERATED = "ReplicatedBy"
EC2 = os.environ['EC2R']            # Especifica el Recurso de EC2 a copiar

tagbusqueda = os.environ['TAGBUSQUEDA']
tagvalor = os.environ['TAGVALOR']
taggeneratedby = 'AutoBackupCRR-'+ os.environ['AMBIENTE']

ec2_client_s = boto3.client('ec2', region_name=S_REGION)
ec2_client_d = boto3.client('ec2', region_name=D_REGION)
rds_client_s = boto3.client('rds', region_name=S_REGION)
rds_client_d = boto3.client('rds', region_name=D_REGION)

"""Function to Copy RDS Snapshots"""
def copy_rds_snapshot(snapshot):
    notReplicated = True
    toReplicate = False
    copia = 0
    error = 0
    if snapshot['Status'] == 'available':
        snap_tags = rds_client_s.list_tags_for_resource(ResourceName=snapshot['DBSnapshotArn']) 
        for tag in snap_tags['TagList']:            # Busca en todos los Tags del Snapshot, TAGBUSQUEDA == TAGVALOR
            if tag.get("Key") == tagbusqueda and tag.get("Value") == tagvalor:
                toReplicate = True
        for tag in snap_tags['TagList']:            # Busca en todos los Tags del Snapshot, replicated == true
            if tag.get("Key") == TAGGENERATED:
                notReplicated = False
        if toReplicate and notReplicated:           # Si no ha sido Replicado
            try:
                if snapshot['Encrypted']:
                    snap_copy = rds_client_d.copy_db_snapshot( # Copia el Snapshot
                        KmsKeyId = 'alias/aws/rds',
                        SourceDBSnapshotIdentifier = snapshot['DBSnapshotArn'],
                        TargetDBSnapshotIdentifier = snapshot['DBSnapshotIdentifier'],
                        CopyTags = True,
                        SourceRegion = S_REGION
                    )
                else:
                    snap_copy = rds_client_d.copy_db_snapshot( # Copia el Snapshot
                        SourceDBSnapshotIdentifier = snapshot['DBSnapshotArn'],
                        TargetDBSnapshotIdentifier = snapshot['DBSnapshotIdentifier'],
                        CopyTags = True,
                        SourceRegion = S_REGION
                    )
                rds_client_d.add_tags_to_resource(  # Establece Tags de Destination Snapshot, replicated == true
                    ResourceName = snap_copy['DBSnapshot']['DBSnapshotArn'],
                    Tags = [{'Key':'ReplicatedFrom','Value':S_REGION}]
                )
                rds_client_s.add_tags_to_resource(  # Establece Tags de Source Snapshot, replicated == true
                    ResourceName = snapshot['DBSnapshotArn'],
                    Tags = [{'Key':TAGGENERATED,'Value':taggeneratedby}]
                )
                copia=1
            except:
                print("Error en Procesado de Snapshot RDS: "+snapshot['DBSnapshotArn'])
                error=1
    return {'Copias': copia, 'Errores': error}

"""Function to Copy Aurora Snapshots"""
def copy_aurora_snapshot(snapshot):
    notReplicated = True
    toReplicate = False
    copia = 0
    error = 0
    if snapshot['Status'] == 'available':
        snap_tags = rds_client_s.list_tags_for_resource(ResourceName=snapshot['DBClusterSnapshotArn']) 
        for tag in snap_tags['TagList']:            # Busca en todos los Tags del Snapshot, TAGBUSQUEDA == TAGVALOR
            if tag.get("Key") == tagbusqueda and tag.get("Value") == tagvalor:
                toReplicate = True
        for tag in snap_tags['TagList']:            # Busca en todos los Tags del Snapshot, replicated == true
            if tag.get("Key") == TAGGENERATED:
                notReplicated = False
        if toReplicate and notReplicated:           # Si no ha sido Replicada 
            try:
                if snapshot['StorageEncrypted']:
                    snap_copy = rds_client_d.copy_db_cluster_snapshot( # Copia el Snapshot
                        KmsKeyId = 'alias/aws/rds',
                        SourceDBClusterSnapshotIdentifier = snapshot['DBClusterSnapshotArn'],
                        TargetDBClusterSnapshotIdentifier = snapshot['DBClusterSnapshotIdentifier'],
                        CopyTags = True,
                        SourceRegion = S_REGION
                    )
                else:
                    snap_copy = rds_client_d.copy_db_cluster_snapshot( # Copia el Snapshot
                        SourceDBClusterSnapshotIdentifier = snapshot['DBClusterSnapshotArn'],
                        TargetDBClusterSnapshotIdentifier = snapshot['DBClusterSnapshotIdentifier'],
                        CopyTags = True,
                        SourceRegion = S_REGION
                    )
                rds_client_d.add_tags_to_resource(  # Establece Tags de Destination Snapshot, replicated == true
                    ResourceName = snap_copy['DBClusterSnapshot']['DBClusterSnapshotArn'],
                    Tags = [{'Key':'ReplicatedFrom','Value':S_REGION}]
                )
                rds_client_s.add_tags_to_resource(  # Establece Tags de Source Snapshot, replicated == true
                    ResourceName = snapshot['DBClusterSnapshotArn'],
                    Tags = [{'Key':TAGGENERATED,'Value':taggeneratedby}]
                )
                copia=1
            except:
                print("Error en Procesado de Snapshot Aurora: "+snapshot['DBClusterSnapshotArn'])
                error=1
    return {'Copias': copia, 'Errores': error}

"""Function to Copy AMIs (Images)"""
def copy_amis():
    copias = 0
    errores = 0
    # Obtiene listado de Imagenes en Source con Tag especificado y que esten Disponibles
    amis = ec2_client_s.describe_images(Filters=[{'Name': 'tag:'+tagbusqueda, 'Values': [tagvalor]},{'Name': 'state', 'Values': ['available']}])

    for ami in amis['Images']:              # Para cada AMI
        replicated = False
        amiTags = ami['Tags']
        for tag in amiTags:                 # Busca en todos los Tags de la AMI, replicated == true
            if tag.get("Key") == TAGGENERATED:
                replicated = True
        if not(replicated):
            try:
                ami_copy = ec2_client_d.copy_image( # Copia la Image
                    ClientToken = str(uuid.uuid4()),
                    Description = ami.get('Description','ReplicatedBy '+taggeneratedby) + ' FROM ' + S_REGION,
                    Name = ami['Name'],
                    SourceImageId = ami['ImageId'],
                    SourceRegion = S_REGION,
                    DryRun=False
                )
                ec2_client_d.create_tags(   # Copia Tags de Image
                    Resources = [ami_copy['ImageId']],
                    Tags = amiTags
                )
                ec2_client_d.create_tags(   # Establece Tags de Destination Image, replicated == true
                    Resources = [ami_copy['ImageId']],
                    Tags = [{'Key':'ReplicatedFrom','Value':S_REGION}]
                )
                ec2_client_s.create_tags(   # Establece Tags de Source Image, replicated == true
                    Resources = [ami['ImageId']],
                    Tags = [{'Key':TAGGENERATED,'Value':taggeneratedby}]
                )
                copias+=1
            except:
                print("Error en Procesado de AMI: "+ami['ImageId'])
                errores+=1
    return {'Copias': copias, 'Errores': errores}

"""Function to Copy EBS Snapshots"""
def copy_snapshots():
    copias = 0
    errores = 0
    # Obtiene listado de Snapshots en Source con Tag especificado y que esten Disponibles
    snapshots = ec2_client_s.describe_snapshots(Filters=[{'Name': 'tag:'+tagbusqueda, 'Values': [tagvalor]},{'Name': 'status', 'Values': ['completed']}])

    for snapshot in snapshots['Snapshots']: # Para cada AMI
        replicated = False
        snapTags = snapshot['Tags']
        for tag in snapTags:                # Busca en todos los Tags del Snapshot, replicated == true
            if tag.get("Key") == TAGGENERATED:
                replicated = True
        if not(replicated):
            try:
                snap_copy = ec2_client_d.copy_snapshot( # Copia Snapshot
                    Description = snapshot.get('Description','ReplicatedBy '+taggeneratedby) + ' FROM ' + S_REGION,
                    SourceSnapshotId = snapshot['SnapshotId'],
                    SourceRegion = S_REGION,
                    DryRun=False
                )
                ec2_client_d.create_tags(   # Copia Tags de Snapshot
                    Resources = [snap_copy['SnapshotId']],
                    Tags = snapTags
                )
                ec2_client_d.create_tags(   # Establece Tags de Destination Image, replicated == true
                    Resources = [snap_copy['SnapshotId']],
                    Tags = [{'Key':'ReplicatedFrom','Value':S_REGION}]
                )
                ec2_client_s.create_tags(   # Establece Tags de Source Image, replicated == true
                    Resources = [snapshot['SnapshotId']],
                    Tags = [{'Key':TAGGENERATED,'Value':taggeneratedby}]
                )
                copias+=1
            except:
                print("Error en Procesado de Snapshot: "+snapshot['SnapshotId'])
                errores+=1
    return {'Copias': copias, 'Errores': errores}

def lambda_handler(event, context):

    errores_ami=0
    copias_ami=0
    errores_aurora=0
    copias_aurora=0    
    errores_rds=0
    copias_rds=0
    errores_snapshot=0
    copias_snapshot=0

    """Inicia replicacion de Imagenes de Instancias"""
    if EC2 == 'AMI':
        cami = copy_amis()
        copias_ami = cami['Copias']
        errores_ami = cami['Errores']

    """Inicia replicacion de Snapshots de Instancias"""
    if EC2 == 'Snapshot':
        csnap = copy_snapshots()
        copias_snapshot = csnap['Copias']
        errores_snapshot = csnap['Errores']

    """Inicia replicacion de Snapshots de Aurora"""
    # Obtiene listado de Snapshots en Source con Tag especificado y que esten Disponibles
    snapshots = rds_client_s.describe_db_cluster_snapshots(
        IncludeShared = False,
        IncludePublic = False
    )
    for snapshot in snapshots['DBClusterSnapshots']:  # Para cada Snapshot
        csnapshot = copy_aurora_snapshot(snapshot)
        copias_aurora+=csnapshot['Copias']
        errores_aurora+=csnapshot['Errores']

    while 'Marker' in snapshots:
        snapshots = rds_client_s.describe_db_cluster_snaphosts(
            Marker = snapshots['Marker'],
            IncludeShared = False,
            IncludePublic = False
        )
        for snapshot in snapshots['DBClusterSnapshots']:  # Para cada Snapshot
            csnapshot = copy_aurora_snapshot(snapshot)
            copias_aurora+=csnapshot['Copias']
            errores_aurora+=csnapshot['Errores']

    """Inicia replicacion de Snapshots RDS"""
    # Obtiene listado de Snapshots en Source con Tag especificado y que esten Disponibles
    snapshots = rds_client_s.describe_db_snapshots(
        IncludeShared = False,
        IncludePublic = False
    )
    for snapshot in snapshots['DBSnapshots']:  # Para cada Snapshot
        csnapshot = copy_rds_snapshot(snapshot)
        copias_rds+=csnapshot['Copias']
        errores_rds+=csnapshot['Errores']

    while 'Marker' in snapshots:
        snapshots = rds_client_s.describe_db_snaphosts(
            Marker = snapshots['Marker'],
            IncludeShared = False,
            IncludePublic = False
        )
        for snapshot in snapshots['DBSnapshots']:  # Para cada Snapshot
            csnapshot = copy_rds_snapshot(snapshot)
            copias_rds+=csnapshot['Copias']
            errores_rds+=csnapshot['Errores']

    return {
        'statusCode': 200,
        'body': json.dumps(
            'Ejecucion Completada, AMIs Copiadas: '+str(copias_ami)+' con '+str(errores_ami)+' Errores. ' + 
            'Aurora Snapshots Copiados: '+str(copias_aurora)+' con '+str(errores_aurora)+' Errores. ' +
            'RDS Snapshots Copiados: '+str(copias_rds)+' con '+str(errores_rds)+' Errores. ' +
            'EBS Snapshots Copiados: '+str(copias_snapshot)+' con '+str(errores_snapshot)+' Errores.'
        )
    }
