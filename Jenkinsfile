pipeline {
    agent any

    environment {
        DJANGO_SETTINGS_MODULE = 'chapp.settings'
        PYTHONDONTWRITEBYTECODE = '1'
        SONAR_SCANNER_HOME = tool('SonarQubeScanner')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup') {
            steps {
                sh '''
                    python -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install flake8 coverage
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    . venv/bin/activate
                    flake8 pms/ --max-line-length=120 --exclude=migrations --format=pylint --output-file=flake8-report.txt || true
                '''
            }
            post {
                always {
                    recordIssues tools: [flake8(pattern: 'flake8-report.txt')]
                }
            }
        }

        stage('Test & Coverage') {
            steps {
                sh '''
                    . venv/bin/activate
                    coverage run --source=pms --omit='*/migrations/*' manage.py test pms -v 2 --testrunner=xmlrunner.extra.djangotestrunner.XMLTestRunner 2>&1 || \
                    coverage run --source=pms --omit='*/migrations/*' manage.py test pms -v 2
                    coverage xml -o coverage.xml
                    coverage report --fail-under=95
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results.xml'
                    cobertura coberturaReportFile: 'coverage.xml'
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh '''
                        ${SONAR_SCANNER_HOME}/bin/sonar-scanner \
                            -Dsonar.projectKey=chapp-booking-engine \
                            -Dsonar.sources=pms \
                            -Dsonar.tests=pms \
                            -Dsonar.test.inclusions=**/tests.py \
                            -Dsonar.exclusions=**/migrations/**,**/statics/**,**/templates/** \
                            -Dsonar.python.coverage.reportPaths=coverage.xml
                    '''
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Build Docker Image') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'staging'
                    branch 'preprod'
                    branch 'main'
                }
            }
            steps {
                script {
                    def tag = "${env.BRANCH_NAME}-${env.BUILD_NUMBER}"
                    sh "docker build -t booking-engine:${tag} ."
                }
            }
        }

        stage('Deploy to Development') {
            when { branch 'develop' }
            steps {
                echo 'Deploying to Development environment...'
                sh '''
                    docker compose -f docker-compose.yml down || true
                    docker compose -f docker-compose.yml up -d
                '''
            }
        }

        stage('Deploy to Staging') {
            when { branch 'staging' }
            steps {
                echo 'Deploying to Staging environment...'
                sh '''
                    docker compose -f docker-compose.staging.yml down || true
                    docker compose -f docker-compose.staging.yml up -d
                '''
            }
        }

        stage('Deploy to Pre-Production') {
            when { branch 'preprod' }
            steps {
                echo 'Deploying to Pre-Production environment...'
                sh '''
                    docker compose -f docker-compose.preprod.yml down || true
                    docker compose -f docker-compose.preprod.yml up -d
                '''
            }
        }

        stage('Deploy to Production') {
            when { branch 'main' }
            steps {
                input message: 'Deploy to Production?', ok: 'Deploy'
                echo 'Deploying to Production environment...'
                sh '''
                    docker compose -f docker-compose.prod.yml down || true
                    docker compose -f docker-compose.prod.yml up -d
                '''
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            echo "Pipeline completed successfully for ${env.BRANCH_NAME}"
        }
        failure {
            echo "Pipeline failed for ${env.BRANCH_NAME}"
        }
    }
}
