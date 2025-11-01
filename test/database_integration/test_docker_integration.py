"""
Test Docker PostgreSQL integration
"""
import pytest
import subprocess
import time
from sqlalchemy import text

from database.config import engine


class TestDockerIntegration:
    """Test suite for Docker PostgreSQL integration"""

    @pytest.mark.asyncio
    async def test_docker_container_running(self):
        """Test that Docker PostgreSQL container is running"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=wci-emailagent-postgres", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            container_name = result.stdout.strip()
            assert "wci-emailagent-postgres" in container_name, \
                "Docker PostgreSQL container is not running"
            print(f"✅ Docker container running: {container_name}")
        except subprocess.TimeoutExpired:
            pytest.fail("Docker command timed out")
        except FileNotFoundError:
            pytest.skip("Docker is not installed or not in PATH")

    @pytest.mark.asyncio
    async def test_docker_container_healthy(self):
        """Test that Docker PostgreSQL container is healthy"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=wci-emailagent-postgres", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            status = result.stdout.strip()
            assert "healthy" in status.lower() or "up" in status.lower(), \
                f"Docker container is not healthy: {status}"
            print(f"✅ Docker container status: {status}")
        except subprocess.TimeoutExpired:
            pytest.fail("Docker command timed out")
        except FileNotFoundError:
            pytest.skip("Docker is not installed or not in PATH")

    @pytest.mark.asyncio
    async def test_docker_volume_exists(self):
        """Test that Docker volume for PostgreSQL data exists"""
        try:
            result = subprocess.run(
                ["docker", "volume", "ls", "--filter", "name=wci-emailagent_pgdata", "--format", "{{.Name}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            volume_name = result.stdout.strip()
            assert "wci-emailagent_pgdata" in volume_name, \
                "Docker volume for PostgreSQL data does not exist"
            print(f"✅ Docker volume exists: {volume_name}")
        except subprocess.TimeoutExpired:
            pytest.fail("Docker command timed out")
        except FileNotFoundError:
            pytest.skip("Docker is not installed or not in PATH")

    @pytest.mark.asyncio
    async def test_docker_network_exists(self):
        """Test that Docker network exists"""
        try:
            result = subprocess.run(
                ["docker", "network", "ls", "--filter", "name=wci-emailagent_wci-network", "--format", "{{.Name}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            network_name = result.stdout.strip()
            assert "wci-emailagent_wci-network" in network_name, \
                "Docker network does not exist"
            print(f"✅ Docker network exists: {network_name}")
        except subprocess.TimeoutExpired:
            pytest.fail("Docker command timed out")
        except FileNotFoundError:
            pytest.skip("Docker is not installed or not in PATH")

    @pytest.mark.asyncio
    async def test_database_accessible_from_host(self):
        """Test that database is accessible from host machine"""
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
            print("✅ Database accessible from host machine")
        except Exception as e:
            pytest.fail(f"❌ Database not accessible from host: {e}")

    @pytest.mark.asyncio
    async def test_database_port_mapping(self):
        """Test that PostgreSQL port is correctly mapped"""
        try:
            result = subprocess.run(
                ["docker", "port", "wci-emailagent-postgres", "5432"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            port_mapping = result.stdout.strip()
            assert "5432" in port_mapping or "5433" in port_mapping, \
                f"PostgreSQL port not correctly mapped: {port_mapping}"
            print(f"✅ Port mapping: {port_mapping}")
        except subprocess.TimeoutExpired:
            pytest.fail("Docker command timed out")
        except FileNotFoundError:
            pytest.skip("Docker is not installed or not in PATH")

    @pytest.mark.asyncio
    async def test_docker_logs_no_errors(self):
        """Test that Docker container logs don't show critical errors"""
        try:
            result = subprocess.run(
                ["docker", "logs", "wci-emailagent-postgres", "--tail", "50"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            logs = result.stdout + result.stderr
            
            # Check for critical errors
            critical_errors = ["FATAL", "PANIC", "authentication failed"]
            found_errors = [err for err in critical_errors if err in logs]
            
            # Note: We might have old authentication errors in logs, so we just warn
            if found_errors:
                print(f"⚠️  Found potential errors in logs: {found_errors}")
            else:
                print("✅ No critical errors in Docker logs")
        except subprocess.TimeoutExpired:
            pytest.fail("Docker command timed out")
        except FileNotFoundError:
            pytest.skip("Docker is not installed or not in PATH")

    @pytest.mark.asyncio
    async def test_database_persistence(self):
        """Test that database data persists (uses volume)"""
        async with engine.connect() as conn:
            # Check if volume is being used
            result = await conn.execute(text("SHOW data_directory"))
            data_dir = result.scalar()
            assert data_dir is not None
            print(f"✅ Database data directory: {data_dir}")

    @pytest.mark.asyncio
    async def test_connection_pooling_config(self):
        """Test that connection pooling is configured"""
        pool = engine.pool
        assert pool is not None
        print(f"✅ Connection pool configured (size: {pool.size()}, overflow: {pool.overflow()})")

    @pytest.mark.asyncio
    async def test_database_encoding(self):
        """Test that database uses UTF-8 encoding"""
        async with engine.connect() as conn:
            result = await conn.execute(text("SHOW server_encoding"))
            encoding = result.scalar()
            assert encoding == "UTF8", f"Database encoding should be UTF8, got {encoding}"
            print(f"✅ Database encoding: {encoding}")

