# AIP index

All approved general AIPs bundled with this skill (upstream commit 23e176e7333e),
grouped the way <https://google.aip.dev/general> groups them. Each entry links to
the local copy and quotes the first sentence of its guidance.

## Meta

- [AIP-1: AIP Purpose and Guidelines](aips/0001-aip-purpose-and-guidelines.md): As the corpus of Google APIs has grown and the API Governance team has grown to meet the demand of supporting them, it is increasingly necessary to have a corpus of documentation for API producers, reviewers, and othe...
- [AIP-2: AIP Numbering](aips/0002-aip-numbering.md): The AIP system provides a mechanism to index and have a single source of truth for API Improvement Proposals, as well as iterate on them collaboratively and transparently.
- [AIP-3: AIP Versioning](aips/0003-aip-versioning.md): This AIP defines the versioning scheme of the AIPs.
- [AIP-200: Precedent](aips/0200-precedent.md): If an API violates the AIP standards for any reason, there must be an internal comment linking to this document using its descriptive link (aip.dev/not-precedent) to ensure others do not copy the violations or cite th...
- [AIP-8: AIP Style and Guidance](aips/0008-aip-style-and-guidance.md): AIP stands for API Improvement Proposal, which is a design document providing high-level, concise documentation for API design and development.
- [AIP-9: Glossary](aips/0009-glossary.md): The following terminology should be used consistently throughout AIPs.

## Process

- [AIP-100: API Design Review FAQ](aips/0100-api-design-review-faq.md): API design review exists to ensure a simple, intuitive, and consistent API experience throughout our API corpus.
- [AIP-205: Beta-blocking changes](aips/0205-beta-blocking-changes.md): If an API has usability concerns or violates API standards, and the present design should receive additional scrutiny before being carried through to the Beta version, there must be an internal comment linking to this...

## API Concepts

- [AIP-111: Planes](aips/0111-planes.md): Management resources and methods exist primarily to provision, configure, and audit the resources that the data plane interfaces with.

## Resource Design

- [AIP-121: Resource-oriented design](aips/0121-resource-oriented-design.md): Resource-oriented design is a pattern for specifying RPC APIs, based on several high-level design principles (most of which are common to recent public HTTP APIs):
- [AIP-122: Resource names](aips/0122-resource-names.md): All resource names defined by an API must be unique within that API.
- [AIP-123: Resource types](aips/0123-resource-types.md): APIs must define a resource type for each resource in the API, according to the following pattern: {Service Name}/{Type}.
- [AIP-124: Resource association](aips/0124-resource-association.md): A resource must have at most one canonical parent, and List requests must not require two distinct "parents" to work.
- [AIP-126: Enumerations](aips/0126-enumerations.md): It is common for a field to only accept or provide a discrete and limited set of values.
- [AIP-128: Declarative-friendly interfaces](aips/0128-declarative-friendly-interfaces.md): Resources that are declarative-friendly must use only strongly-consistent standard methods for managing resource lifecycle, which allows tools to support these resources generically, as well as conforming to other dec...
- [AIP-129: Server-Modified Values and Defaults](aips/0129-server-modified-values-and-defaults.md): Fields must have a single owner, whether that is the client or the server.
- [AIP-156: Singleton resources](aips/0156-singleton-resources.md): An API may define singleton resources.
- [AIP-236: Policy preview](aips/0236-policy-preview.md): A policy is a resource that provides rules that admit or deny access to other resources.

## Operations

- [AIP-130: Methods](aips/0130-methods.md): The following enumerates multiple categories of methods that exist, often grouped up under some object (e.g. collection or resource) that the method operates upon.
- [AIP-131: Standard methods: Get](aips/0131-standard-methods-get.md): APIs must provide a get method for resources.
- [AIP-132: Standard methods: List](aips/0132-standard-methods-list.md): APIs must provide a List method for resources unless the resource is a singleton.
- [AIP-133: Standard methods: Create](aips/0133-standard-methods-create.md): APIs should generally provide a create method for resources unless it is not valuable for users to do so.
- [AIP-134: Standard methods: Update](aips/0134-standard-methods-update.md): APIs should generally provide an update method for resources unless it is not valuable for users to do so.
- [AIP-135: Standard methods: Delete](aips/0135-standard-methods-delete.md): APIs should generally provide a delete method for resources unless it is not valuable for users to do so.
- [AIP-136: Custom methods](aips/0136-custom-methods.md): Custom methods should only be used for functionality that can not be easily expressed via standard methods; prefer standard methods if possible, due to their consistent semantics.
- [AIP-151: Long-running operations](aips/0151-long-running-operations.md): Individual API methods that might take a significant amount of time to complete should return a google.longrunning.Operation object instead of the ultimate response message.
- [AIP-231: Batch methods: Get](aips/0231-batch-methods-get.md): Some APIs need to allow users to get a specific set of resources at a consistent time point (e.g. using a read transaction).
- [AIP-233: Batch methods: Create](aips/0233-batch-methods-create.md): Some APIs need to allow users to create multiple resources in a single transaction.
- [AIP-234: Batch methods: Update](aips/0234-batch-methods-update.md): Some APIs need to allow users to modify a set of resources in a single transaction.
- [AIP-235: Batch methods: Delete](aips/0235-batch-methods-delete.md): Some APIs need to allow users to delete a set of resources in a single transaction.

## Fields

- [AIP-140: Field names](aips/0140-field-names.md): Field names should be in correct American English.
- [AIP-202: Fields](aips/0202-fields.md): Decorating a field with google.api.field_info is only necessary when explicitly stated in this AIP or another that leverages google.api.FieldInfo information.
- [AIP-203: Field behavior documentation](aips/0203-field-behavior-documentation.md): APIs use the google.api.field_behavior annotation to describe well-understood field behavior, such as a field being required or immutable.
- [AIP-141: Quantities](aips/0141-quantities.md): Quantities with a clear unit of measurement (such as bytes, miles, and so on) must include the unit of measurement as the suffix.
- [AIP-142: Time and duration](aips/0142-time-and-duration.md): Fields representing time should use the common, generally used components (such as google.protobuf.Timestamp or google.type.Date) for representing time or duration types.
- [AIP-143: Standardized codes](aips/0143-standardized-codes.md): For concepts where a standardized code exists and is in common use, fields representing these concepts should use the standardized code for both input and output.
- [AIP-144: Repeated fields](aips/0144-repeated-fields.md): Resources may use repeated fields where appropriate.
- [AIP-145: Ranges](aips/0145-ranges.md): Services often need to represent ranges of discrete or continuous values.
- [AIP-146: Generic fields](aips/0146-generic-fields.md): While generic fields are generally rare, a service may introduce generic field where necessary.
- [AIP-147: Sensitive fields](aips/0147-sensitive-fields.md): If the sensitive information is required for the resource as a whole to exist, the data should be accepted as an input-only field with no corresponding output field.
- [AIP-148: Standard fields](aips/0148-standard-fields.md): Standard fields should be used to describe their corresponding concept, and should not be used for any other purpose.
- [AIP-149: Unset field values](aips/0149-unset-field-values.md): Services defined in protocol buffers should use the optional keyword for primitives if and only if it is necessary to distinguish setting the field to its default value (0, false, or empty string) from not setting it...
- [AIP-216: States](aips/0216-states.md): Resources needing to communicate their state should use an enum, which should be called State (or, if more specificity is required, end in the word State).

## Design Patterns

- [AIP-152: Jobs](aips/0152-jobs.md): Occasionally, APIs may need to expose a task that takes significant time to complete, and where a transient long-running operation is not appropriate.
- [AIP-153: Import and export](aips/0153-import-and-export.md): APIs may support import and export operations, which may create multiple new resources, or they may populate data into a single resource.
- [AIP-154: Resource freshness validation](aips/0154-resource-freshness-validation.md): APIs often need to validate that a client and server agree on the current state of a resource before taking some kind of action on that resource.
- [AIP-155: Request identification](aips/0155-request-identification.md): APIs may add a string request_id parameter to request messages (including those of standard methods) in order to uniquely identify particular requests.
- [AIP-157: Partial responses](aips/0157-partial-responses.md): Sometimes, a resource can be either large or expensive to compute, and the API needs to give the user control over which fields it sends back.
- [AIP-158: Pagination](aips/0158-pagination.md): RPCs returning collections of data must provide pagination at the outset, as it is a backwards-incompatible change to add pagination to an existing method.
- [AIP-159: Reading across collections](aips/0159-reading-across-collections.md): Sometimes, it is useful for a user to be able to retrieve resources across multiple collections, or retrieve a single resource without needing to know what collection it is in.
- [AIP-160: Filtering](aips/0160-filtering.md): APIs may provide filtering to users on List methods (or similar methods to query a collection, such as Search).
- [AIP-161: Field masks](aips/0161-field-masks.md): Often, when updating resources (using an update method as defined in AIP-134 or something reasonably similar), it is desirable to specify exactly which fields are being updated, so that the service can ignore the rest...
- [AIP-163: Change validation](aips/0163-change-validation.md): APIs may provide an option to validate, but not actually execute, a request, and provide the same response (status code, headers, and response body) that it would have provided if the request was actually executed.
- [AIP-164: Soft delete](aips/0164-soft-delete.md): APIs may support the ability to "undelete", to allow for situations where users mistakenly delete resources and need the ability to recover.
- [AIP-165: Criteria-based delete](aips/0165-criteria-based-delete.md): An API may implement a Purge method to permit deleting a large number of resources based on a filter string; however, this should only be done if the Batch Delete (AIP-235) pattern is insufficient to accomplish the de...
- [AIP-210: Unicode](aips/0210-unicode.md): In API documentation (e.g., API reference documents, blog posts, marketing documentation, billing explanations, etc), "character" must be defined as a Unicode code point.
- [AIP-211: Authorization checks](aips/0211-authorization-checks.md): Services must check authorization before validating any request, to ensure both a secure API surface and a consistent user experience.
- [AIP-214: Resource expiration](aips/0214-resource-expiration.md): APIs wishing to convey an expiration must rely on a google.protobuf.Timestamp field called expire_time.
- [AIP-217: Unreachable resources](aips/0217-unreachable-resources.md): Occasionally, a user may ask for a list of resources, and some set of resources in the list are temporarily unavailable.

## Compatibility and Versioning

- [AIP-180: Backwards compatibility](aips/0180-backwards-compatibility.md): Existing client code must not be broken by a service updating to a new minor or patch release.
- [AIP-181: Stability levels](aips/0181-stability-levels.md): While different organizations (both inside Google and outside) have different product life cycles, AIPs refer to the stability of an API component using the following terms.
- [AIP-184: API version identifiers](aips/0184-api-version-identifiers.md): Version identifiers can be used at a granularity level finer than identifiers used for channel-, release-, and visibility-based versioning described in AIP-185.
- [AIP-185: API Versioning](aips/0185-api-versioning.md): All Google API interfaces must provide a major version number, which is encoded at the end of the protobuf package, and included as the first part of the URI path for REST APIs.

## Polish

- [AIP-190: Naming conventions](aips/0190-naming-conventions.md): This topic describes the naming conventions used in Google APIs.
- [AIP-191: File and directory structure](aips/0191-file-and-directory-structure.md): APIs defined in protocol buffers must use proto3 syntax.
- [AIP-192: Documentation](aips/0192-documentation.md): In APIs defined in protocol buffers, public comments must be included over every component (service, method, message, field, enum, and enum value) using the protocol buffers comment format.
- [AIP-193: Errors](aips/0193-errors.md): Services must return a google.rpc.Status message when an API error occurs, and must use the canonical error codes defined in google.rpc.Code.
- [AIP-194: Automatic retry configuration](aips/0194-automatic-retry-configuration.md): Clients should automatically retry requests for which repeated runs would not cause unintended state changes, which are non-transactional, and which are unary.

## Protocol buffers

- [AIP-127: HTTP and gRPC Transcoding](aips/0127-http-and-grpc-transcoding.md): APIs must provide HTTP definitions for each RPC that they define, except for bi-directional streaming RPCs, which can not be natively supported using HTTP/1.1.
- [AIP-213: Common components](aips/0213-common-components.md): As specified in AIP-215, APIs must be self-contained except for the use of "common component" packages which are intended for use by multiple APIs.
- [AIP-215: API-specific protos](aips/0215-api-specific-protos.md): APIs are mostly defined in terms of protos which are API-specific, with occasional dependencies on common components.
