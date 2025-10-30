"use strict";
/**
 * OpenAPI Documentation for PersonaEngine API
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.openApiSpec = void 0;
exports.openApiSpec = {
    openapi: "3.0.0",
    info: {
        title: "PersonaEngine API",
        description: "Unified TypeScript Express microservices ecosystem with workflow builder gateway and persona management system",
        version: "2.0.0",
        contact: {
            name: "PersonaEngine Support",
            email: "support@personaengine.ai"
        }
    },
    servers: [
        {
            url: "http://localhost:8000/api/v1",
            description: "Development server"
        }
    ],
    security: [
        {
            bearerAuth: []
        }
    ],
    components: {
        securitySchemes: {
            bearerAuth: {
                type: "http",
                scheme: "bearer",
                bearerFormat: "token"
            }
        },
        schemas: {
            BrainAskRequest: {
                type: "object",
                required: ["question"],
                properties: {
                    persona_id: {
                        type: "string",
                        description: "ID of the persona to provide context",
                        example: "P0001"
                    },
                    question: {
                        type: "string",
                        description: "Question to ask the AI brain",
                        example: "What can you tell me about this generation job?"
                    },
                    context: {
                        type: "object",
                        description: "Additional context for the query",
                        additionalProperties: true,
                        example: {
                            "project_type": "portrait_session",
                            "client_notes": "Looking for natural lighting advice"
                        }
                    }
                }
            },
            BrainAskResponse: {
                type: "object",
                properties: {
                    ok: {
                        type: "boolean",
                        example: true
                    },
                    mode: {
                        type: "string",
                        enum: ["live", "fake"],
                        example: "live"
                    },
                    answer: {
                        type: "string",
                        example: "Based on the vault context, this studio session generated 6 images with artistic portrait traits. The generation used natural lighting techniques with a creative approach."
                    },
                    tokens_used: {
                        type: "number",
                        example: 125
                    },
                    error: {
                        type: "string",
                        nullable: true
                    }
                }
            },
            PersonaAddSystemRequest: {
                type: "object",
                required: ["id", "name", "role"],
                properties: {
                    id: {
                        type: "string",
                        pattern: "^U\\d+$",
                        description: "System persona ID starting with 'U' followed by numbers",
                        example: "U0002"
                    },
                    name: {
                        type: "string",
                        description: "Display name for the system persona",
                        example: "Marketing Assistant"
                    },
                    role: {
                        type: "string",
                        enum: ["upsell", "system"],
                        description: "Role of the system persona",
                        example: "upsell"
                    },
                    traits: {
                        type: "array",
                        items: {
                            type: "string"
                        },
                        description: "Personality traits for the persona",
                        example: ["commercial", "persuasive", "data-driven"]
                    }
                }
            },
            PersonaAddSystemResponse: {
                type: "object",
                properties: {
                    ok: {
                        type: "boolean",
                        example: true
                    },
                    system_persona: {
                        type: "object",
                        properties: {
                            id: {
                                type: "string",
                                example: "U0002"
                            },
                            name: {
                                type: "string",
                                example: "Marketing Assistant"
                            },
                            role: {
                                type: "string",
                                example: "upsell"
                            },
                            traits: {
                                type: "array",
                                items: {
                                    type: "string"
                                },
                                example: ["commercial", "persuasive", "data-driven"]
                            },
                            created_at: {
                                type: "string",
                                format: "date-time",
                                example: "2025-09-28T06:00:00.000Z"
                            },
                            system: {
                                type: "boolean",
                                example: true
                            }
                        }
                    },
                    error: {
                        type: "string",
                        nullable: true
                    }
                }
            },
            UpsellSuggestRequest: {
                type: "object",
                required: ["user_id"],
                properties: {
                    user_id: {
                        type: "string",
                        description: "ID of the user requesting upsell suggestions",
                        example: "U0001"
                    },
                    persona_id: {
                        type: "string",
                        description: "ID of the persona for context",
                        example: "P0001"
                    },
                    job_id: {
                        type: "string",
                        description: "ID of the completed job",
                        example: "J0001"
                    },
                    style: {
                        type: "string",
                        description: "Style of the generation job",
                        example: "studio"
                    },
                    intent: {
                        type: "string",
                        enum: ["prints", "social", "licensing", "followup"],
                        description: "Type of upsell intent",
                        example: "prints"
                    },
                    tone: {
                        type: "string",
                        enum: ["friendly", "assertive"],
                        description: "Tone for the suggestions",
                        example: "friendly"
                    }
                }
            },
            UpsellSuggestion: {
                type: "object",
                properties: {
                    title: {
                        type: "string",
                        description: "Short title (max 6 words)",
                        example: "Premium Print Package"
                    },
                    copy: {
                        type: "string",
                        description: "One sentence description",
                        example: "Transform your 3 studio images into professional gallery-quality prints with multiple sizes and premium paper options."
                    },
                    cta: {
                        type: "string",
                        description: "Call-to-action text",
                        example: "Order Prints"
                    },
                    price_hint: {
                        type: "string",
                        description: "Optional price range",
                        example: "$45-75"
                    },
                    assets: {
                        type: "array",
                        items: {
                            type: "string"
                        },
                        description: "List of included assets",
                        example: ["3 high-resolution files", "Multiple size options", "Premium paper choices"]
                    }
                }
            },
            UpsellSuggestResponse: {
                type: "object",
                properties: {
                    ok: {
                        type: "boolean",
                        example: true
                    },
                    mode: {
                        type: "string",
                        enum: ["live", "fake"],
                        example: "live"
                    },
                    suggestions: {
                        type: "array",
                        items: {
                            $ref: "#/components/schemas/UpsellSuggestion"
                        },
                        description: "Array of upsell suggestions",
                        maxItems: 3
                    },
                    context: {
                        type: "object",
                        properties: {
                            user_id: {
                                type: "string"
                            },
                            persona_id: {
                                type: "string"
                            },
                            job_id: {
                                type: "string"
                            },
                            style: {
                                type: "string"
                            },
                            intent: {
                                type: "string"
                            },
                            images_count: {
                                type: "number"
                            }
                        }
                    },
                    error: {
                        type: "string",
                        nullable: true
                    }
                }
            },
            ErrorResponse: {
                type: "object",
                properties: {
                    ok: {
                        type: "boolean",
                        example: false
                    },
                    error: {
                        type: "string",
                        example: "Missing required field: question (string)"
                    }
                }
            }
        }
    },
    paths: {
        "/brain.ask": {
            post: {
                operationId: "askBrain",
                summary: "Ask the AI brain assistant",
                description: "Query the Claude AI brain with persona context and vault data for intelligent responses about generation jobs and creative workflows",
                tags: ["AI Brain"],
                security: [{ bearerAuth: [] }],
                requestBody: {
                    required: true,
                    content: {
                        "application/json": {
                            schema: {
                                $ref: "#/components/schemas/BrainAskRequest"
                            },
                            examples: {
                                basic_question: {
                                    summary: "Basic question without context",
                                    value: {
                                        question: "What are best practices for studio portrait photography?"
                                    }
                                },
                                persona_context: {
                                    summary: "Question with persona context",
                                    value: {
                                        persona_id: "P0001",
                                        question: "What can you tell me about this generation job?",
                                        context: {
                                            "session_type": "portrait",
                                            "lighting": "natural"
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                responses: {
                    200: {
                        description: "Successful brain response",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/BrainAskResponse"
                                }
                            }
                        }
                    },
                    400: {
                        description: "Bad request - validation error",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    401: {
                        description: "Unauthorized - missing or invalid Bearer token",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    429: {
                        description: "Rate limit exceeded (30 requests per minute)",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/persona.add_system": {
            post: {
                operationId: "addSystemPersona",
                summary: "Register system persona",
                description: "Create a new system-only persona with U-prefix ID for internal operations like upsell generation",
                tags: ["Persona Management"],
                security: [{ bearerAuth: [] }],
                requestBody: {
                    required: true,
                    content: {
                        "application/json": {
                            schema: {
                                $ref: "#/components/schemas/PersonaAddSystemRequest"
                            },
                            examples: {
                                upsell_assistant: {
                                    summary: "Upsell assistant persona",
                                    value: {
                                        id: "U0002",
                                        name: "Marketing Assistant",
                                        role: "upsell",
                                        traits: ["commercial", "persuasive", "data-driven"]
                                    }
                                },
                                system_helper: {
                                    summary: "System helper persona",
                                    value: {
                                        id: "U0003",
                                        name: "Technical Support",
                                        role: "system",
                                        traits: ["helpful", "technical", "precise"]
                                    }
                                }
                            }
                        }
                    }
                },
                responses: {
                    200: {
                        description: "System persona created successfully",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/PersonaAddSystemResponse"
                                }
                            }
                        }
                    },
                    400: {
                        description: "Bad request - validation error",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    401: {
                        description: "Unauthorized - missing or invalid Bearer token",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    429: {
                        description: "Rate limit exceeded (30 requests per minute)",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/upsell.suggest": {
            post: {
                operationId: "suggestUpsells",
                summary: "Generate upsell suggestions",
                description: "Generate 3 tailored upsell suggestions using vault context, job manifest data, and AI-powered recommendations",
                tags: ["Upsell Engine"],
                security: [{ bearerAuth: [] }],
                requestBody: {
                    required: true,
                    content: {
                        "application/json": {
                            schema: {
                                $ref: "#/components/schemas/UpsellSuggestRequest"
                            },
                            examples: {
                                print_upsell: {
                                    summary: "Print-focused upsell",
                                    value: {
                                        user_id: "U0001",
                                        persona_id: "P0001",
                                        job_id: "J0001",
                                        style: "studio",
                                        intent: "prints",
                                        tone: "friendly"
                                    }
                                },
                                social_upsell: {
                                    summary: "Social media upsell",
                                    value: {
                                        user_id: "U0001",
                                        persona_id: "P0001",
                                        job_id: "J0002",
                                        style: "portrait",
                                        intent: "social",
                                        tone: "assertive"
                                    }
                                },
                                basic_upsell: {
                                    summary: "Basic upsell without job context",
                                    value: {
                                        user_id: "U0001",
                                        intent: "followup"
                                    }
                                }
                            }
                        }
                    }
                },
                responses: {
                    200: {
                        description: "Upsell suggestions generated successfully",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/UpsellSuggestResponse"
                                }
                            }
                        }
                    },
                    400: {
                        description: "Bad request - validation error",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    401: {
                        description: "Unauthorized - missing or invalid Bearer token",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    },
                    429: {
                        description: "Rate limit exceeded (30 requests per minute)",
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
};
//# sourceMappingURL=openapi.js.map