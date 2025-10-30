import axios, { AxiosResponse } from 'axios';
import { logger } from '../log';

const BASE_URL = 'http://localhost:3000/api/v1';

interface TestResult {
  name: string;
  passed: boolean;
  response?: any;
  error?: string;
}

class SmokeTest {
  private results: TestResult[] = [];
  private createdPersonaId: string | null = null;
  private createdJobId: string | null = null;

  async run(): Promise<void> {
    console.log('🧪 Starting smoke tests...\n');
    
    await this.testPersonaNew();
    await this.testGen();
    await this.testGenMore();
    await this.testVaultOpen();
    
    this.printResults();
    this.exit();
  }

  private async testPersonaNew(): Promise<void> {
    try {
      logger.info('Testing POST /persona.new');
      
      const response: AxiosResponse = await axios.post(`${BASE_URL}/persona.new`, {
        name: 'Smoke Test Persona',
        traits: ['test', 'automated', 'smoke'],
        refs: ['smoke_test_run']
      });
      
      const passed = response.data.ok === true && response.data.persona && response.data.persona.id;
      
      if (passed) {
        this.createdPersonaId = response.data.persona.id;
        logger.info(`✅ Persona created: ${this.createdPersonaId}`);
      }
      
      this.results.push({
        name: 'POST /persona.new',
        passed,
        response: response.data
      });
      
    } catch (error: any) {
      logger.error('❌ Persona creation failed:', error.message);
      this.results.push({
        name: 'POST /persona.new',
        passed: false,
        error: error.message
      });
    }
  }

  private async testGen(): Promise<void> {
    try {
      logger.info('Testing POST /gen');
      
      if (!this.createdPersonaId) {
        throw new Error('No persona ID available from previous test');
      }
      
      const response: AxiosResponse = await axios.post(`${BASE_URL}/gen`, {
        persona_id: this.createdPersonaId,
        style: 'studio',
        count: 1,
        slots: {
          outfit: 'smoke test outfit',
          mood: 'confident',
          setting: 'test studio'
        },
        seed: 12345
      });
      
      const passed = response.data.ok === true && 
                    response.data.job_id && 
                    response.data.images && 
                    Array.isArray(response.data.images);
      
      if (passed) {
        this.createdJobId = response.data.job_id;
        logger.info(`✅ Generation completed: ${this.createdJobId}`);
      }
      
      this.results.push({
        name: 'POST /gen',
        passed,
        response: response.data
      });
      
    } catch (error: any) {
      logger.error('❌ Generation failed:', error.message);
      this.results.push({
        name: 'POST /gen',
        passed: false,
        error: error.message
      });
    }
  }

  private async testGenMore(): Promise<void> {
    try {
      logger.info('Testing POST /gen.more');
      
      if (!this.createdPersonaId || !this.createdJobId) {
        throw new Error('No persona ID or job ID available from previous tests');
      }
      
      const response: AxiosResponse = await axios.post(`${BASE_URL}/gen.more`, {
        persona_id: this.createdPersonaId,
        job_id: this.createdJobId,
        count: 1
      });
      
      // For now, gen.more returns 501, so we expect that
      const passed = response.status === 501 && response.data.ok === false;
      
      logger.info('ℹ️ gen.more returned expected 501 (not implemented)');
      
      this.results.push({
        name: 'POST /gen.more',
        passed,
        response: response.data
      });
      
    } catch (error: any) {
      // Check if it's the expected 501 error
      if (error.response && error.response.status === 501) {
        logger.info('ℹ️ gen.more returned expected 501 (not implemented)');
        this.results.push({
          name: 'POST /gen.more',
          passed: true,
          response: error.response.data
        });
      } else {
        logger.error('❌ gen.more failed unexpectedly:', error.message);
        this.results.push({
          name: 'POST /gen.more',
          passed: false,
          error: error.message
        });
      }
    }
  }

  private async testVaultOpen(): Promise<void> {
    try {
      logger.info('Testing GET /vault.open');
      
      if (!this.createdPersonaId || !this.createdJobId) {
        throw new Error('No persona ID or job ID available from previous tests');
      }
      
      const response: AxiosResponse = await axios.get(`${BASE_URL}/vault.open`, {
        params: {
          persona_id: this.createdPersonaId,
          job_id: this.createdJobId,
          style: 'studio'
        }
      });
      
      const passed = response.data.ok === true && response.data.link;
      
      if (passed) {
        logger.info(`✅ Vault link retrieved: ${response.data.link}`);
      }
      
      this.results.push({
        name: 'GET /vault.open',
        passed,
        response: response.data
      });
      
    } catch (error: any) {
      logger.error('❌ Vault open failed:', error.message);
      this.results.push({
        name: 'GET /vault.open',
        passed: false,
        error: error.message
      });
    }
  }

  private printResults(): void {
    console.log('\n🧪 Smoke Test Results:');
    console.log('━'.repeat(50));
    
    this.results.forEach(result => {
      const status = result.passed ? '✅ PASS' : '❌ FAIL';
      console.log(`${status} ${result.name}`);
      
      if (!result.passed && result.error) {
        console.log(`   Error: ${result.error}`);
      }
    });
    
    const totalTests = this.results.length;
    const passedTests = this.results.filter(r => r.passed).length;
    
    console.log('━'.repeat(50));
    console.log(`📊 Summary: ${passedTests}/${totalTests} tests passed`);
    
    if (passedTests === totalTests) {
      console.log('🎉 All smoke tests passed!');
    } else {
      console.log('💥 Some smoke tests failed!');
    }
  }

  private exit(): void {
    const allPassed = this.results.every(r => r.passed);
    process.exit(allPassed ? 0 : 1);
  }
}

// Run smoke tests if called directly
if (require.main === module) {
  const smokeTest = new SmokeTest();
  smokeTest.run().catch(error => {
    console.error('💥 Smoke test suite crashed:', error);
    process.exit(1);
  });
}

export default SmokeTest;