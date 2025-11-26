            logger.error(f"\nERROR: Processing failed: {result.error_message}")
            return 1

    except KeyboardInterrupt:
        logger.warning("\nProcess interrupted by user.")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())