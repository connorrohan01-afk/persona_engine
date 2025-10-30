"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const axios_1 = __importDefault(require("axios"));
const log_1 = require("../log");
const BASE_URL = 'http://localhost:3000/api/v1';
class SmokeTest {
    constructor() {
        this.results = [];
        this.createdPersonaId = null;
        this.createdJobId = null;
    }
    async run() {
        console.log('🧪 Starting smoke tests...\n');
        await this.testPersonaNew();
        await this.testGen();
        await this.testGenMore();
        await this.testVaultOpen();
        this.printResults();
        this.exit();
    }
    async testPersonaNew() {
        try {
            log_1.logger.info('Testing POST /persona.new');
            const response = await axios_1.default.post(`${BASE_URL}/persona.new`, {
                name: 'Smoke Test Persona',
                traits: ['test', 'automated', 'smoke'],
                refs: ['smoke_test_run']
            });
            const passed = response.data.ok === true && response.data.persona && response.data.persona.id;
            if (passed) {
                this.createdPersonaId = response.data.persona.id;
                log_1.logger.info(`✅ Persona created: ${this.createdPersonaId}`);
            }
            this.results.push({
                name: 'POST /persona.new',
                passed,
                response: response.data
            });
        }
        catch (error) {
            log_1.logger.error('❌ Persona creation failed:', error.message);
            this.results.push({
                name: 'POST /persona.new',
                passed: false,
                error: error.message
            });
        }
    }
    async testGen() {
        try {
            log_1.logger.info('Testing POST /gen');
            if (!this.createdPersonaId) {
                throw new Error('No persona ID available from previous test');
            }
            const response = await axios_1.default.post(`${BASE_URL}/gen`, {
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
                log_1.logger.info(`✅ Generation completed: ${this.createdJobId}`);
            }
            this.results.push({
                name: 'POST /gen',
                passed,
                response: response.data
            });
        }
        catch (error) {
            log_1.logger.error('❌ Generation failed:', error.message);
            this.results.push({
                name: 'POST /gen',
                passed: false,
                error: error.message
            });
        }
    }
    async testGenMore() {
        try {
            log_1.logger.info('Testing POST /gen.more');
            if (!this.createdPersonaId || !this.createdJobId) {
                throw new Error('No persona ID or job ID available from previous tests');
            }
            const response = await axios_1.default.post(`${BASE_URL}/gen.more`, {
                persona_id: this.createdPersonaId,
                job_id: this.createdJobId,
                count: 1
            });
            // For now, gen.more returns 501, so we expect that
            const passed = response.status === 501 && response.data.ok === false;
            log_1.logger.info('ℹ️ gen.more returned expected 501 (not implemented)');
            this.results.push({
                name: 'POST /gen.more',
                passed,
                response: response.data
            });
        }
        catch (error) {
            // Check if it's the expected 501 error
            if (error.response && error.response.status === 501) {
                log_1.logger.info('ℹ️ gen.more returned expected 501 (not implemented)');
                this.results.push({
                    name: 'POST /gen.more',
                    passed: true,
                    response: error.response.data
                });
            }
            else {
                log_1.logger.error('❌ gen.more failed unexpectedly:', error.message);
                this.results.push({
                    name: 'POST /gen.more',
                    passed: false,
                    error: error.message
                });
            }
        }
    }
    async testVaultOpen() {
        try {
            log_1.logger.info('Testing GET /vault.open');
            if (!this.createdPersonaId || !this.createdJobId) {
                throw new Error('No persona ID or job ID available from previous tests');
            }
            const response = await axios_1.default.get(`${BASE_URL}/vault.open`, {
                params: {
                    persona_id: this.createdPersonaId,
                    job_id: this.createdJobId,
                    style: 'studio'
                }
            });
            const passed = response.data.ok === true && response.data.link;
            if (passed) {
                log_1.logger.info(`✅ Vault link retrieved: ${response.data.link}`);
            }
            this.results.push({
                name: 'GET /vault.open',
                passed,
                response: response.data
            });
        }
        catch (error) {
            log_1.logger.error('❌ Vault open failed:', error.message);
            this.results.push({
                name: 'GET /vault.open',
                passed: false,
                error: error.message
            });
        }
    }
    printResults() {
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
        }
        else {
            console.log('💥 Some smoke tests failed!');
        }
    }
    exit() {
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
exports.default = SmokeTest;
//# sourceMappingURL=smoke.js.map