/**
 * OpenAPI Documentation for PersonaEngine API
 */
export declare const openApiSpec: {
    openapi: string;
    info: {
        title: string;
        description: string;
        version: string;
        contact: {
            name: string;
            email: string;
        };
    };
    servers: {
        url: string;
        description: string;
    }[];
    security: {
        bearerAuth: never[];
    }[];
    components: {
        securitySchemes: {
            bearerAuth: {
                type: string;
                scheme: string;
                bearerFormat: string;
            };
        };
        schemas: {
            BrainAskRequest: {
                type: string;
                required: string[];
                properties: {
                    persona_id: {
                        type: string;
                        description: string;
                        example: string;
                    };
                    question: {
                        type: string;
                        description: string;
                        example: string;
                    };
                    context: {
                        type: string;
                        description: string;
                        additionalProperties: boolean;
                        example: {
                            project_type: string;
                            client_notes: string;
                        };
                    };
                };
            };
            BrainAskResponse: {
                type: string;
                properties: {
                    ok: {
                        type: string;
                        example: boolean;
                    };
                    mode: {
                        type: string;
                        enum: string[];
                        example: string;
                    };
                    answer: {
                        type: string;
                        example: string;
                    };
                    tokens_used: {
                        type: string;
                        example: number;
                    };
                    error: {
                        type: string;
                        nullable: boolean;
                    };
                };
            };
            PersonaAddSystemRequest: {
                type: string;
                required: string[];
                properties: {
                    id: {
                        type: string;
                        pattern: string;
                        description: string;
                        example: string;
                    };
                    name: {
                        type: string;
                        description: string;
                        example: string;
                    };
                    role: {
                        type: string;
                        enum: string[];
                        description: string;
                        example: string;
                    };
                    traits: {
                        type: string;
                        items: {
                            type: string;
                        };
                        description: string;
                        example: string[];
                    };
                };
            };
            PersonaAddSystemResponse: {
                type: string;
                properties: {
                    ok: {
                        type: string;
                        example: boolean;
                    };
                    system_persona: {
                        type: string;
                        properties: {
                            id: {
                                type: string;
                                example: string;
                            };
                            name: {
                                type: string;
                                example: string;
                            };
                            role: {
                                type: string;
                                example: string;
                            };
                            traits: {
                                type: string;
                                items: {
                                    type: string;
                                };
                                example: string[];
                            };
                            created_at: {
                                type: string;
                                format: string;
                                example: string;
                            };
                            system: {
                                type: string;
                                example: boolean;
                            };
                        };
                    };
                    error: {
                        type: string;
                        nullable: boolean;
                    };
                };
            };
            UpsellSuggestRequest: {
                type: string;
                required: string[];
                properties: {
                    user_id: {
                        type: string;
                        description: string;
                        example: string;
                    };
                    persona_id: {
                        type: string;
                        description: string;
                        example: string;
                    };
                    job_id: {
                        type: string;
                        description: string;
                        example: string;
                    };
                    style: {
                        type: string;
                        description: string;
                        example: string;
                    };
                    intent: {
                        type: string;
                        enum: string[];
                        description: string;
                        example: string;
                    };
                    tone: {
                        type: string;
                        enum: string[];
                        description: string;
                        example: string;
                    };
                };
            };
            UpsellSuggestion: {
                type: string;
                properties: {
                    title: {
                        type: string;
                        description: string;
                        example: string;
                    };
                    copy: {
                        type: string;
                        description: string;
                        example: string;
                    };
                    cta: {
                        type: string;
                        description: string;
                        example: string;
                    };
                    price_hint: {
                        type: string;
                        description: string;
                        example: string;
                    };
                    assets: {
                        type: string;
                        items: {
                            type: string;
                        };
                        description: string;
                        example: string[];
                    };
                };
            };
            UpsellSuggestResponse: {
                type: string;
                properties: {
                    ok: {
                        type: string;
                        example: boolean;
                    };
                    mode: {
                        type: string;
                        enum: string[];
                        example: string;
                    };
                    suggestions: {
                        type: string;
                        items: {
                            $ref: string;
                        };
                        description: string;
                        maxItems: number;
                    };
                    context: {
                        type: string;
                        properties: {
                            user_id: {
                                type: string;
                            };
                            persona_id: {
                                type: string;
                            };
                            job_id: {
                                type: string;
                            };
                            style: {
                                type: string;
                            };
                            intent: {
                                type: string;
                            };
                            images_count: {
                                type: string;
                            };
                        };
                    };
                    error: {
                        type: string;
                        nullable: boolean;
                    };
                };
            };
            ErrorResponse: {
                type: string;
                properties: {
                    ok: {
                        type: string;
                        example: boolean;
                    };
                    error: {
                        type: string;
                        example: string;
                    };
                };
            };
        };
    };
    paths: {
        "/brain.ask": {
            post: {
                operationId: string;
                summary: string;
                description: string;
                tags: string[];
                security: {
                    bearerAuth: never[];
                }[];
                requestBody: {
                    required: boolean;
                    content: {
                        "application/json": {
                            schema: {
                                $ref: string;
                            };
                            examples: {
                                basic_question: {
                                    summary: string;
                                    value: {
                                        question: string;
                                    };
                                };
                                persona_context: {
                                    summary: string;
                                    value: {
                                        persona_id: string;
                                        question: string;
                                        context: {
                                            session_type: string;
                                            lighting: string;
                                        };
                                    };
                                };
                            };
                        };
                    };
                };
                responses: {
                    200: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                    400: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                    401: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                    429: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                };
            };
        };
        "/persona.add_system": {
            post: {
                operationId: string;
                summary: string;
                description: string;
                tags: string[];
                security: {
                    bearerAuth: never[];
                }[];
                requestBody: {
                    required: boolean;
                    content: {
                        "application/json": {
                            schema: {
                                $ref: string;
                            };
                            examples: {
                                upsell_assistant: {
                                    summary: string;
                                    value: {
                                        id: string;
                                        name: string;
                                        role: string;
                                        traits: string[];
                                    };
                                };
                                system_helper: {
                                    summary: string;
                                    value: {
                                        id: string;
                                        name: string;
                                        role: string;
                                        traits: string[];
                                    };
                                };
                            };
                        };
                    };
                };
                responses: {
                    200: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                    400: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                    401: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                    429: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                };
            };
        };
        "/upsell.suggest": {
            post: {
                operationId: string;
                summary: string;
                description: string;
                tags: string[];
                security: {
                    bearerAuth: never[];
                }[];
                requestBody: {
                    required: boolean;
                    content: {
                        "application/json": {
                            schema: {
                                $ref: string;
                            };
                            examples: {
                                print_upsell: {
                                    summary: string;
                                    value: {
                                        user_id: string;
                                        persona_id: string;
                                        job_id: string;
                                        style: string;
                                        intent: string;
                                        tone: string;
                                    };
                                };
                                social_upsell: {
                                    summary: string;
                                    value: {
                                        user_id: string;
                                        persona_id: string;
                                        job_id: string;
                                        style: string;
                                        intent: string;
                                        tone: string;
                                    };
                                };
                                basic_upsell: {
                                    summary: string;
                                    value: {
                                        user_id: string;
                                        intent: string;
                                    };
                                };
                            };
                        };
                    };
                };
                responses: {
                    200: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                    400: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                    401: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                    429: {
                        description: string;
                        content: {
                            "application/json": {
                                schema: {
                                    $ref: string;
                                };
                            };
                        };
                    };
                };
            };
        };
    };
};
//# sourceMappingURL=openapi.d.ts.map