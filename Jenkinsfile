pipeline {
    agent any

    // These become available as environment variables throughout the pipeline
    environment {
        APP_NAME        = 'flask-app'
        REGISTRY        = 'localhost:5000'
        IMAGE_NAME      = "${REGISTRY}/${APP_NAME}"
        // Use the Git commit SHA as the image tag — you can always trace
        // exactly which commit is running in production
        IMAGE_TAG       = "${env.GIT_COMMIT?.take(7) ?: 'latest'}"
        KUBECONFIG_CRED = credentials('kubeconfig')
    }

    options {
        // Keep only last 10 builds to save disk space
        buildDiscarder(logRotator(numToKeepStr: '10'))
        // Fail the build if it runs longer than 20 minutes
        timeout(time: 20, unit: 'MINUTES')
        // Don't run concurrent builds of the same branch
        disableConcurrentBuilds()
    }

    stages {

        stage('Checkout') {
            steps {
                echo "📥 Checking out source code..."
                checkout scm
                // Print what commit we're building — useful for debugging
                sh 'git log --oneline -5'
            }
        }

        stage('Run Tests') {
            steps {
                echo "🧪 Running test suite..."
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    pip install pytest
                    python -m pytest tests/ -v --tb=short
                '''
            }
            post {
                always {
                    // Clean up virtualenv
                    sh 'rm -rf venv'
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "🐳 Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"
                script {
                    // docker.build() returns an image object we can reuse
                    dockerImage = docker.build(
                        "${IMAGE_NAME}:${IMAGE_TAG}",
                        "--label git-commit=${env.GIT_COMMIT} ."
                    )
                }
            }
        }

        stage('Security Scan') {
            steps {
                echo "🔐 Scanning image for vulnerabilities..."
                // Trivy is a great free scanner — install it on the Jenkins node
                // This stage WARNS on findings but doesn't fail the build
                // Adjust --exit-code to 1 when you're ready to enforce
                sh """
                    trivy image --exit-code 0 \
                        --severity HIGH,CRITICAL \
                        --no-progress \
                        ${IMAGE_NAME}:${IMAGE_TAG}
                """
            }
        }

        stage('Push to Registry') {
            steps {
                echo "📤 Pushing image to registry..."
                script {
                    // Push with the commit SHA tag
                    dockerImage.push("${IMAGE_TAG}")
                    // Also tag as 'latest' so K8s manifests can use it
                    dockerImage.push('latest')
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                echo "☸️ Deploying to Kubernetes..."
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh """
                        # Update the image tag in the deployment manifest on the fly
                        # This way your manifest always reflects the exact image deployed
                        sed -i 's|image: .*flask-app.*|image: ${IMAGE_NAME}:${IMAGE_TAG}|g' \
                            k8s/deployment.yaml

                        # Apply manifests — kubectl is idempotent, so this is safe to re-run
                        kubectl apply -f k8s/deployment.yaml
                        kubectl apply -f k8s/service.yaml

                        # Wait for the rollout to complete before declaring success
                        # If pods fail to start, this command will fail and alert you
                        kubectl rollout status deployment/${APP_NAME} --timeout=120s
                    """
                }
            }
        }

        stage('Smoke Test') {
            steps {
                echo "💨 Running smoke test against deployed app..."
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh """
                        # Port-forward in the background for the test
                        kubectl port-forward service/flask-app-service 8888:80 &
                        PF_PID=\$!
                        sleep 3

                        # Hit the health endpoint — fail the build if it's not 200
                        HTTP_CODE=\$(curl -s -o /dev/null -w "%{http_code}" \
                            http://localhost:8888/health)
                        
                        kill \$PF_PID

                        if [ "\$HTTP_CODE" != "200" ]; then
                            echo "❌ Smoke test failed! Got HTTP \$HTTP_CODE"
                            exit 1
                        fi
                        echo "✅ Smoke test passed!"
                    """
                }
            }
        }
    }

    post {
        success {
            echo """
            ✅ Pipeline succeeded!
            Image: ${IMAGE_NAME}:${IMAGE_TAG}
            Access your app at: http://flask-app.local
            """
        }
        failure {
            echo "❌ Pipeline failed. Check the logs above for details."
            // Add email/Slack notification here when ready:
            // mail to: 'team@example.com', subject: "Build Failed: ${env.JOB_NAME}"
        }
        always {
            // Always clean up dangling Docker images to prevent disk fill-up
            sh 'docker image prune -f'
            cleanWs()
        }
    }
}
